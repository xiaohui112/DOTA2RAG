"""数据版本追踪模块——管理 data/version_meta.json 的读写"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

import httpx

logger = logging.getLogger(__name__)

DEFAULT_META_PATH = Path("data/version_meta.json")

OPENDOTA_BASE_URL = "https://api.opendota.com"


def _empty_meta() -> Dict[str, Any]:
    """返回默认的空版本元信息结构"""
    return {
        "last_updated": None,
        "game_version": None,
        "sources": {},
    }


class VersionTracker:
    """数据版本追踪管理器"""

    def __init__(self, meta_path: Optional[Path] = None):
        """
        初始化版本追踪器。

        Args:
            meta_path: version_meta.json 文件路径，默认 data/version_meta.json
        """
        self.meta_path = meta_path or DEFAULT_META_PATH

    def read_version_meta(self) -> Dict[str, Any]:
        """
        读取版本元信息。

        - 文件不存在：返回默认空结构
        - 文件损坏（JSON 解析失败）：记录警告，重建文件，返回空结构

        Returns:
            版本元信息字典
        """
        if not self.meta_path.exists():
            logger.info(f"版本元信息文件不存在: {self.meta_path}，返回默认结构")
            return _empty_meta()

        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 确保基本结构完整
            if not isinstance(data, dict):
                raise ValueError("顶层不是字典")
            data.setdefault("last_updated", None)
            data.setdefault("game_version", None)
            data.setdefault("sources", {})
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"版本元信息文件损坏 ({e})，重新创建空文件")
            meta = _empty_meta()
            self._write_meta(meta)
            return meta

    def update_source_meta(
        self,
        source: str,
        count: int,
        **extra,
    ) -> None:
        """
        更新单个数据源的元信息。

        Args:
            source: 数据源名称（heroes/items/abilities/patches/wiki）
            count: 文档数量
            **extra: 额外字段（如 latest_patch）
        """
        meta = self.read_version_meta()
        now = datetime.now(timezone.utc).isoformat()

        source_info = meta.get("sources", {}).get(source, {})
        source_info["count"] = count
        source_info["updated_at"] = now
        source_info.update(extra)

        meta.setdefault("sources", {})[source] = source_info
        meta["last_updated"] = now

        # 如果补丁数据有 latest_patch，更新全局 game_version
        patches_info = meta.get("sources", {}).get("patches", {})
        if patches_info.get("latest_patch"):
            meta["game_version"] = patches_info["latest_patch"]

        self._write_meta(meta)
        logger.info(f"已更新 {source} 元信息: count={count}, extra={extra}")

    def check_freshness(self) -> Dict[str, Any]:
        """
        检查数据是否需要更新。

        查询 OpenDota API 获取远程数据源计数和补丁列表，
        与本地元信息比对，返回各数据源的更新状态摘要。

        Returns:
            {
                "needs_update": bool,
                "details": {
                    "heroes": {"local": int, "remote": int, "needs_update": bool, "message": str},
                    "items": {...},
                    "patches": {"local_latest": str, "remote_latest": str, "missing": [str], ...},
                    ...
                }
            }
        """
        meta = self.read_version_meta()
        sources = meta.get("sources", {})
        result = {"needs_update": False, "details": {}}

        try:
            with httpx.Client(timeout=15.0) as client:
                # 检查英雄数量
                try:
                    resp = client.get(f"{OPENDOTA_BASE_URL}/api/heroes")
                    resp.raise_for_status()
                    remote_heroes = len(resp.json())
                    local_heroes = sources.get("heroes", {}).get("count", 0)
                    heroes_needs = remote_heroes != local_heroes
                    result["details"]["heroes"] = {
                        "local": local_heroes,
                        "remote": remote_heroes,
                        "needs_update": heroes_needs,
                        "message": (
                            f"heroes: {local_heroes} → {remote_heroes}, 需要更新"
                            if heroes_needs
                            else f"heroes: {local_heroes} 个, 已是最新"
                        ),
                    }
                    if heroes_needs:
                        result["needs_update"] = True
                except Exception as e:
                    result["details"]["heroes"] = {
                        "error": str(e),
                        "needs_update": False,
                        "message": f"heroes: 检查失败 ({e})",
                    }

                # 检查物品数量
                try:
                    resp = client.get(f"{OPENDOTA_BASE_URL}/api/constants/items")
                    resp.raise_for_status()
                    remote_items = len(resp.json())
                    local_items = sources.get("items", {}).get("count", 0)
                    items_needs = remote_items != local_items
                    result["details"]["items"] = {
                        "local": local_items,
                        "remote": remote_items,
                        "needs_update": items_needs,
                        "message": (
                            f"items: {local_items} → {remote_items}, 需要更新"
                            if items_needs
                            else f"items: {local_items} 个, 已是最新"
                        ),
                    }
                    if items_needs:
                        result["needs_update"] = True
                except Exception as e:
                    result["details"]["items"] = {
                        "error": str(e),
                        "needs_update": False,
                        "message": f"items: 检查失败 ({e})",
                    }

                # 检查补丁版本
                try:
                    resp = client.get(f"{OPENDOTA_BASE_URL}/api/constants/patch")
                    resp.raise_for_status()
                    patches_data = resp.json()

                    # 提取所有版本号
                    remote_versions = []
                    if isinstance(patches_data, list):
                        remote_versions = [p.get("name", "") for p in patches_data if p.get("name")]
                    elif isinstance(patches_data, dict):
                        remote_versions = list(patches_data.keys())

                    local_latest = sources.get("patches", {}).get("latest_patch", "")
                    remote_latest = remote_versions[-1] if remote_versions else ""

                    # 找出本地缺失的版本
                    missing = []
                    if local_latest and remote_versions:
                        try:
                            idx = remote_versions.index(local_latest)
                            missing = remote_versions[idx + 1:]
                        except ValueError:
                            missing = remote_versions  # 全部缺失
                    elif not local_latest:
                        missing = remote_versions

                    patches_needs = len(missing) > 0
                    result["details"]["patches"] = {
                        "local_latest": local_latest or "(无)",
                        "remote_latest": remote_latest,
                        "missing_count": len(missing),
                        "missing_versions": missing[-10:],  # 最多显示最新10个
                        "needs_update": patches_needs,
                        "message": (
                            f"patches: 缺少 {len(missing)} 个版本 (最新: {remote_latest})"
                            if patches_needs
                            else f"patches: 已是最新 ({remote_latest})"
                        ),
                    }
                    if patches_needs:
                        result["needs_update"] = True
                except Exception as e:
                    result["details"]["patches"] = {
                        "error": str(e),
                        "needs_update": False,
                        "message": f"patches: 检查失败 ({e})",
                    }

        except Exception as e:
            logger.error(f"数据新鲜度检查失败: {e}")
            result["error"] = str(e)

        return result

    def _write_meta(self, meta: Dict[str, Any]) -> None:
        """将元信息写入 JSON 文件"""
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
