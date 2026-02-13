"""从 OpenDota API 或 DOTA2 官方 API 获取物品数据"""
import logging
from typing import List, Dict, Any, Optional

import httpx

from .http_client import RateLimitedClient

logger = logging.getLogger(__name__)

OPENDOTA_BASE_URL = "https://api.opendota.com"
DOTA2_ITEMLIST_URL = "https://www.dota2.com/datafeed/itemlist"

# DOTA2 官方 API 请求头
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_items_from_official(language: str = "schinese") -> List[Dict[str, Any]]:
    """
    从 DOTA2 官方 API 获取物品数据（包含中文名称）
    
    Args:
        language: 语言代码，默认为 schinese（简体中文）
    
    Returns:
        物品数据列表，每个物品包含完整属性信息
    """
    logger.info(f"开始从 DOTA2 官方 API 获取物品数据 (language={language})...")
    
    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            response = client.get(
                DOTA2_ITEMLIST_URL,
                params={"language": language}
            )
            response.raise_for_status()
            data = response.json()
            
            # 解析数据结构: result.data.itemabilities
            items_data = data.get("result", {}).get("data", {}).get("itemabilities", [])
            
            result = []
            for item_info in items_data:
                # 处理合成配方
                recipes = []
                if item_info.get("recipes"):
                    for recipe in item_info["recipes"]:
                        if isinstance(recipe, dict) and "items" in recipe:
                            recipes.extend(recipe["items"])
                
                item = {
                    "id": item_info.get("id"),
                    "name": item_info.get("name", ""),
                    "name_loc": item_info.get("name_loc", ""),  # 中文名称
                    "name_english_loc": item_info.get("name_english_loc", ""),  # 英文名称
                    "neutral_item_tier": item_info.get("neutral_item_tier", -1),
                    "is_pregame_suggested": item_info.get("is_pregame_suggested", False),
                    "is_earlygame_suggested": item_info.get("is_earlygame_suggested", False),
                    "is_lategame_suggested": item_info.get("is_lategame_suggested", False),
                    "recipes": recipes,  # 合成配方物品 ID 列表
                }
                result.append(item)
            
            logger.info(f"成功从 DOTA2 官方 API 获取 {len(result)} 个物品的数据")
            return result
            
    except Exception as e:
        logger.error(f"从 DOTA2 官方 API 获取物品数据失败: {e}")
        logger.info("降级到 OpenDota API")
        return fetch_items_from_opendota()


def fetch_items_from_opendota() -> List[Dict[str, Any]]:
    """
    从 OpenDota API 获取所有物品数据（备用方案）
    
    Returns:
        物品数据列表，每个物品包含完整属性信息
    """
    logger.info("开始从 OpenDota API 获取物品数据...")
    
    with RateLimitedClient(OPENDOTA_BASE_URL) as client:
        response = client.get("/api/constants/items")
        items_data = response.json()
        
        result = []
        for item_id, item_info in items_data.items():
            # 处理物品数据
            item = {
                "id": item_id,
                "name": item_info.get("dname", ""),
                "cost": item_info.get("cost", 0),
                "secret_shop": item_info.get("secret_shop", 0),
                "side_shop": item_info.get("side_shop", 0),
                "recipe": item_info.get("recipe", 0),
                "components": item_info.get("components", []),
                # 属性加成
                "attrib": item_info.get("attrib", []),
                "mc": item_info.get("mc", 0),  # 魔法消耗
                "cd": item_info.get("cd", 0),  # 冷却时间
                "qual": item_info.get("qual", ""),  # 品质
                "notes": item_info.get("notes", ""),  # 说明
                "desc": item_info.get("desc", ""),  # 描述
                "lore": item_info.get("lore", ""),  # 背景故事
                "hint": item_info.get("hint", []),  # 提示
            }
            result.append(item)
        
        logger.info(f"成功从 OpenDota API 获取 {len(result)} 个物品的数据")
        return result


def fetch_items(use_official: bool = True, language: str = "schinese") -> List[Dict[str, Any]]:
    """
    获取物品数据，优先使用 DOTA2 官方 API
    
    Args:
        use_official: 是否优先使用官方 API，默认为 True
        language: 语言代码（仅官方 API 使用），默认为 schinese
    
    Returns:
        物品数据列表，每个物品包含完整属性信息
    """
    if use_official:
        return fetch_items_from_official(language=language)
    else:
        return fetch_items_from_opendota()
