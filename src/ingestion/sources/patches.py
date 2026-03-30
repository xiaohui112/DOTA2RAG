"""
从 Dota 2 官方 datafeed API 获取完整版本列表和详细 Patch Notes。

数据源：
  - 版本列表: https://www.dota2.com/datafeed/patchnoteslist
  - 版本详情: https://www.dota2.com/datafeed/patchnotes?version=xxx
"""
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional

import httpx

from .patch_scraper import scrape_patch_notes, batch_scrape_patches

logger = logging.getLogger(__name__)

# Dota 2 官方版本列表 API
DOTA2_PATCHLIST_URL = "https://www.dota2.com/datafeed/patchnoteslist"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _fetch_patch_list() -> List[Dict[str, Any]]:
    """
    从 Dota 2 官方 API 获取完整的补丁版本列表（含子版本如 7.40a/b/c）。

    Returns:
        版本列表，每项包含 patch_number, patch_name, patch_timestamp
    """
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(
                DOTA2_PATCHLIST_URL,
                params={"language": "schinese"},
                headers={
                    **DEFAULT_HEADERS,
                    "referer": "https://www.dota2.com/patches/",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            patches = data.get("patches", [])
            logger.info(f"从 Dota 2 官方 API 获取到 {len(patches)} 个版本")
            return patches

    except Exception as e:
        logger.error(f"获取版本列表失败: {e}")
        return []


def _timestamp_to_date(ts: int) -> str:
    """将 Unix 时间戳转为 ISO 日期字符串（东八区）"""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(ts, tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return ""


def fetch_patches(since_version: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取补丁版本列表 + 每个版本的详细 Patch Notes（中文）。

    流程：
      1. 从 Dota 2 官方 patchnoteslist API 获取完整版本列表（含子版本）
      2. 按 since_version 过滤（增量模式）
      3. 对每个版本调用 patchnotes datafeed API 获取详细中文变更内容

    Args:
        since_version: 可选，从该版本开始获取补丁（包含该版本本身）

    Returns:
        版本更新列表
    """
    logger.info("开始获取 Patch Notes（使用 Dota 2 官方 API）...")

    # 1. 获取完整版本列表
    all_patches = _fetch_patch_list()
    if not all_patches:
        logger.warning("未获取到任何版本信息")
        return []

    # 转换为统一格式
    patch_list = []
    for p in all_patches:
        patch_list.append({
            "name": p.get("patch_number", p.get("patch_name", "")),
            "date": _timestamp_to_date(p.get("patch_timestamp", 0)),
            "timestamp": p.get("patch_timestamp", 0),
        })

    # 2. 增量模式过滤
    if since_version and patch_list:
        filtered = _filter_patches_since(patch_list, since_version)
        if not filtered:
            logger.info(f"未找到版本 {since_version} 或之后的补丁")
            return []
        logger.info(f"增量模式: 过滤出 {len(filtered)} 个版本 (从 {since_version} 开始，包含该版本)")
        patch_list = filtered

    # 3. 从 Dota 2 官方 datafeed API 获取每个版本的详细变更
    versions_to_scrape = [p["name"] for p in patch_list if p.get("name")]

    scraped_data: Dict[str, Dict] = {}
    if versions_to_scrape:
        logger.info(f"准备从官方 API 获取 {len(versions_to_scrape)} 个版本的详细内容...")
        try:
            scraped_results = batch_scrape_patches(versions_to_scrape)
            scraped_data = {r["version"]: r for r in scraped_results}
            logger.info(f"成功获取 {len(scraped_data)} 个版本的详细变更")
        except Exception as e:
            logger.warning(f"官方 Patch Notes 获取失败: {e}")

    # 4. 合并输出
    result = []
    for patch in patch_list:
        version = patch["name"]
        date = patch["date"]
        timestamp = patch.get("timestamp", 0)
        scraped = scraped_data.get(version, {})

        patch_entry = {
            "name": version,
            "date": date,
            "timestamp": timestamp,
            "general_changes": scraped.get("general_changes", []),
            "hero_changes": scraped.get("hero_changes", []),
            "item_changes": scraped.get("item_changes", []),
            "neutral_item_changes": scraped.get("neutral_item_changes", []),
        }
        result.append(patch_entry)

    with_content = sum(
        1 for p in result
        if p.get("general_changes") or p.get("hero_changes") or p.get("item_changes")
    )
    logger.info(
        f"成功获取 {len(result)} 个版本的数据 "
        f"(其中 {with_content} 个包含详细变更内容)"
    )
    return result


def _filter_patches_since(
    patch_list: List[Dict[str, Any]],
    since_version: str,
) -> List[Dict[str, Any]]:
    """过滤出 since_version 及之后的补丁（包含指定版本）"""
    names = [p.get("name", "") for p in patch_list]
    try:
        idx = names.index(since_version)
        return patch_list[idx:]  # 包含指定版本本身
    except ValueError:
        logger.warning(f"未找到版本 {since_version}，返回全部补丁")
        return patch_list
