"""从 Dota 2 官方 datafeed API 获取结构化 Patch Notes"""
import json
import logging
import time
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Dota 2 官方 API
DOTA2_DATAFEED_URL = "https://www.dota2.com/datafeed/patchnotes"
DOTA2_HEROLIST_URL = "https://www.dota2.com/datafeed/herolist"
DOTA2_ABILITYLIST_URL = "https://www.dota2.com/datafeed/abilitylist"

# OpenDota API（用于技能/物品 ID → 名称映射，英雄用官方 API）
OPENDOTA_BASE_URL = "https://api.opendota.com"

# 请求头
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 请求间隔（秒）
REQUEST_INTERVAL = 2.0


# ── ID → 名称映射缓存 ──────────────────────────────────────

_hero_id_map: Optional[Dict[int, str]] = None
_ability_id_map: Optional[Dict[int, str]] = None
_item_id_map: Optional[Dict[int, str]] = None


def _load_hero_id_map() -> Dict[int, str]:
    """
    从 Dota 2 官方 herolist API 加载 hero_id → 中文英雄名 映射。
    优先使用官方中文名，降级到 OpenDota 英文名。
    """
    global _hero_id_map
    if _hero_id_map is not None:
        return _hero_id_map

    # 优先从 Dota 2 官方 API 获取（有中文名）
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                DOTA2_HEROLIST_URL,
                params={"language": "schinese"},
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
            heroes = data.get("result", {}).get("data", {}).get("heroes", [])
            if heroes:
                _hero_id_map = {
                    h["id"]: h.get("name_loc", h.get("name_english_loc", f"Hero #{h['id']}"))
                    for h in heroes
                }
                logger.info(f"已从 Dota 2 官方 API 加载 {len(_hero_id_map)} 个英雄中文名映射")
                return _hero_id_map
    except Exception as e:
        logger.warning(f"从 Dota 2 官方 API 加载英雄映射失败: {e}，降级到 OpenDota")

    # 降级：从 OpenDota API 获取（英文名）
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{OPENDOTA_BASE_URL}/api/heroes")
            resp.raise_for_status()
            heroes = resp.json()
            _hero_id_map = {
                h["id"]: h.get("localized_name", h.get("name", f"Hero #{h['id']}"))
                for h in heroes
            }
            logger.info(f"已从 OpenDota 加载 {len(_hero_id_map)} 个英雄英文名映射")
    except Exception as e:
        logger.warning(f"加载英雄 ID 映射全部失败: {e}")
        _hero_id_map = {}

    return _hero_id_map


def _load_ability_id_map() -> Dict[int, str]:
    """
    从 DOTA2 官方 API 加载 ability_id → 技能中文名称 映射。
    优先使用官方中文名，降级到 OpenDota 英文名。
    """
    global _ability_id_map
    if _ability_id_map is not None:
        return _ability_id_map

    # 优先从 Dota 2 官方 API 获取（有中文名）
    try:
        with httpx.Client(timeout=15.0, headers=DEFAULT_HEADERS) as client:
            resp = client.get(
                DOTA2_ABILITYLIST_URL,
                params={"language": "schinese"},
            )
            resp.raise_for_status()
            data = resp.json()
            abilities = data.get("result", {}).get("data", {}).get("itemabilities", [])
            
            if abilities:
                _ability_id_map = {}
                for ability in abilities:
                    ability_id = ability.get("id")
                    if ability_id is not None:
                        # 优先使用中文名，降级到英文名，最后使用内部名称
                        name = (
                            ability.get("name_loc") or
                            ability.get("name_english_loc") or
                            ability.get("name", f"Ability #{ability_id}")
                        )
                        _ability_id_map[ability_id] = name
                
                logger.info(f"已从 Dota 2 官方 API 加载 {len(_ability_id_map)} 个技能中文名映射")
                return _ability_id_map
    except Exception as e:
        logger.warning(f"从 Dota 2 官方 API 加载技能映射失败: {e}，降级到 OpenDota")

    # 降级：从 OpenDota API 获取（英文名）
    try:
        with httpx.Client(timeout=15.0) as client:
            # ability_ids: {id_str: internal_name}
            resp1 = client.get(f"{OPENDOTA_BASE_URL}/api/constants/ability_ids")
            resp1.raise_for_status()
            id2internal = resp1.json()

            # abilities: {internal_name: {dname, ...}}
            resp2 = client.get(f"{OPENDOTA_BASE_URL}/api/constants/abilities")
            resp2.raise_for_status()
            abilities = resp2.json()

            _ability_id_map = {}
            for id_str, internal_name in id2internal.items():
                try:
                    aid = int(id_str)
                except ValueError:
                    continue
                info = abilities.get(internal_name, {})
                dname = info.get("dname", "") if isinstance(info, dict) else ""
                _ability_id_map[aid] = dname or internal_name

            logger.info(f"已从 OpenDota 加载 {len(_ability_id_map)} 个技能英文名映射")
    except Exception as e:
        logger.warning(f"加载技能 ID 映射全部失败: {e}")
        _ability_id_map = {}

    return _ability_id_map


def _load_item_id_map() -> Dict[int, str]:
    """从 OpenDota API 加载 item_id → 物品显示名称 映射"""
    global _item_id_map
    if _item_id_map is not None:
        return _item_id_map

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{OPENDOTA_BASE_URL}/api/constants/items")
            resp.raise_for_status()
            items = resp.json()
            _item_id_map = {}
            for key, val in items.items():
                if isinstance(val, dict) and "id" in val:
                    _item_id_map[val["id"]] = val.get("dname", key)
            logger.info(f"已加载 {len(_item_id_map)} 个物品 ID 映射")
    except Exception as e:
        logger.warning(f"加载物品 ID 映射失败: {e}")
        _item_id_map = {}

    return _item_id_map


def _get_hero_name(hero_id: int) -> str:
    """通过 hero_id 获取英雄名称"""
    m = _load_hero_id_map()
    return m.get(hero_id, f"Hero #{hero_id}")


def _get_ability_name(ability_id: int) -> str:
    """通过 ability_id 获取技能名称"""
    m = _load_ability_id_map()
    return m.get(ability_id, f"Ability #{ability_id}")


def _get_item_name(ability_id: int) -> str:
    """通过物品的 ability_id 获取物品名称（物品在 datafeed 中也用 ability_id 标识）"""
    item_map = _load_item_id_map()
    name = item_map.get(ability_id)
    if name:
        return name
    # 降级到技能名称映射
    return _get_ability_name(ability_id)


def _clean_html_tags(text: str) -> str:
    """移除简单的 HTML 标签（如 <font>、<br>、<span>），保留文本内容"""
    import re
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


# ── 核心抓取函数 ─────────────────────────────────────────────

def fetch_patch_data(version: str, language: str = "schinese", max_retries: int = 2) -> Dict[str, Any]:
    """
    从 Dota 2 官方 datafeed API 获取指定版本的 Patch Notes JSON 数据。

    Args:
        version: 版本号，如 "7.40"、"7.40c"
        language: 语言代码，默认 "schinese"（简体中文）
        max_retries: 最大重试次数

    Returns:
        API 返回的原始 JSON 字典，失败返回空字典
    """
    params = {"version": version, "language": language}
    headers = {
        **DEFAULT_HEADERS,
        "referer": f"https://www.dota2.com/patches/{version}",
    }

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(
                    DOTA2_DATAFEED_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 404:
                    logger.warning(f"Patch Notes 不存在: {version} (404)")
                    return {}

                response.raise_for_status()
                data = response.json()

                if not data.get("success", True) is False:
                    logger.info(f"成功获取 Patch Notes {version} (JSON datafeed)")
                    return data
                else:
                    logger.warning(f"Patch Notes API 返回 success=false: {version}")
                    return {}

        except httpx.TimeoutException:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(f"请求超时，{wait}s 后重试 ({attempt + 1}/{max_retries + 1}): {version}")
                time.sleep(wait)
            else:
                logger.error(f"请求超时，已达最大重试次数: {version}")
                return {}

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning(f"速率限制 429，{wait}s 后重试: {version}")
                time.sleep(wait)
            elif attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(f"HTTP {e.response.status_code}，{wait}s 后重试: {version}")
                time.sleep(wait)
            else:
                logger.error(f"HTTP 请求失败: {e}")
                return {}

        except Exception as e:
            logger.error(f"抓取异常: {e}")
            return {}

    return {}


def parse_patch_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 datafeed API 返回的原始 JSON 解析为统一的结构化格式。

    Args:
        raw_data: datafeed API 返回的原始 JSON

    Returns:
        {
            "version": str,
            "timestamp": int,
            "general_changes": [str, ...],
            "hero_changes": [{"hero_name": str, "changes": [str]}, ...],
            "item_changes": [{"item_name": str, "changes": [str]}, ...],
            "neutral_item_changes": [{"item_name": str, "changes": [str]}, ...],
            "neutral_creep_changes": [...],
        }
    """
    version = raw_data.get("patch_name", raw_data.get("patch_number", ""))
    timestamp = raw_data.get("patch_timestamp", 0)

    result = {
        "version": version,
        "timestamp": timestamp,
        "general_changes": [],
        "hero_changes": [],
        "item_changes": [],
        "neutral_item_changes": [],
    }

    # 1. 通用改动 (general_notes)
    for section in raw_data.get("general_notes", []):
        title = section.get("title", "")
        notes = section.get("generic", [])
        section_lines = []
        if title:
            section_lines.append(f"【{title}】")
        for note in notes:
            text = _clean_html_tags(note.get("note", ""))
            if not text or text == "":
                continue
            indent = note.get("indent_level", 1) - 1
            prefix = "  " * indent + "- " if indent > 0 else "- "
            section_lines.append(f"{prefix}{text}")
        if section_lines:
            result["general_changes"].extend(section_lines)

    # 2. 英雄改动 (heroes)
    for hero_data in raw_data.get("heroes", []):
        hero_id = hero_data.get("hero_id", 0)
        hero_name = _get_hero_name(hero_id)
        changes = []

        # 英雄基础改动
        for note in hero_data.get("hero_notes", []):
            text = _clean_html_tags(note.get("note", ""))
            if text:
                changes.append(text)

        # 天赋改动
        talent_notes = hero_data.get("talent_notes", [])
        if talent_notes:
            changes.append("[天赋]")
            for note in talent_notes:
                text = _clean_html_tags(note.get("note", ""))
                if text:
                    changes.append(f"  {text}")

        # 技能改动
        for ability_data in hero_data.get("abilities", []):
            ability_id = ability_data.get("ability_id", 0)
            ability_name = _get_ability_name(ability_id)
            changes.append(f"[{ability_name}]")
            for note in ability_data.get("ability_notes", []):
                text = _clean_html_tags(note.get("note", ""))
                if text:
                    changes.append(f"  {text}")

        if changes:
            result["hero_changes"].append({
                "hero_name": hero_name,
                "hero_id": hero_id,
                "changes": changes,
            })

    # 3. 物品改动 (items)
    for item_data in raw_data.get("items", []):
        ability_id = item_data.get("ability_id", 0)
        item_name = _get_item_name(ability_id) if ability_id > 0 else item_data.get("title", "物品")

        changes = []

        # 是否为总括性说明
        if item_data.get("is_general_note"):
            title = item_data.get("title", "")
            if title:
                changes.append(title)
        else:
            for note in item_data.get("ability_notes", []):
                text = _clean_html_tags(note.get("note", ""))
                if text:
                    changes.append(text)

        if changes:
            result["item_changes"].append({
                "item_name": item_name,
                "ability_id": ability_id,
                "changes": changes,
            })

    # 4. 中立物品改动 (neutral_items)
    for ni_data in raw_data.get("neutral_items", []):
        ability_id = ni_data.get("ability_id", 0)
        item_name = _get_item_name(ability_id) if ability_id > 0 else ni_data.get("title", "中立物品")

        changes = []
        if ni_data.get("is_general_note"):
            title = ni_data.get("title", "")
            if title:
                changes.append(title)
        else:
            for note in ni_data.get("ability_notes", []):
                text = _clean_html_tags(note.get("note", ""))
                if text:
                    changes.append(text)

        if changes:
            result["neutral_item_changes"].append({
                "item_name": item_name,
                "ability_id": ability_id,
                "changes": changes,
            })

    return result


def scrape_patch_notes(version: str, language: str = "schinese") -> Dict[str, Any]:
    """
    获取并解析指定版本的 Patch Notes（主函数）。

    Args:
        version: 版本号，如 "7.40"、"7.40c"
        language: 语言代码，默认简体中文

    Returns:
        结构化补丁数据，失败返回带版本号的空结构
    """
    raw_data = fetch_patch_data(version, language=language)

    if not raw_data:
        logger.warning(f"无法获取版本 {version} 的 Patch Notes")
        return {
            "version": version,
            "general_changes": [],
            "hero_changes": [],
            "item_changes": [],
            "neutral_item_changes": [],
        }

    return parse_patch_data(raw_data)


def batch_scrape_patches(versions: List[str], language: str = "schinese") -> List[Dict[str, Any]]:
    """
    批量获取多个版本的 Patch Notes。

    逐个请求，每次请求之间间隔 2 秒，单个版本失败不影响其他版本。

    Args:
        versions: 版本号列表
        language: 语言代码

    Returns:
        成功获取的结构化结果列表
    """
    results = []
    total = len(versions)

    for i, version in enumerate(versions):
        logger.info(f"批量获取进度: {i + 1}/{total} - 版本 {version}")

        patch_data = scrape_patch_notes(version, language=language)

        has_content = (
            patch_data.get("general_changes")
            or patch_data.get("hero_changes")
            or patch_data.get("item_changes")
            or patch_data.get("neutral_item_changes")
        )
        if has_content:
            results.append(patch_data)
        else:
            logger.warning(f"版本 {version} 未获取到有效的 Patch Notes 内容")

        # 请求间隔
        if i < total - 1:
            time.sleep(REQUEST_INTERVAL)

    logger.info(f"批量获取完成: {len(results)}/{total} 个版本成功")
    return results
