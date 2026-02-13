"""从 OpenDota API 获取英雄技能数据，并合并官方 API 的中文名称"""
import logging
from typing import List, Dict, Any, Optional

import httpx

from .http_client import RateLimitedClient

logger = logging.getLogger(__name__)

OPENDOTA_BASE_URL = "https://api.opendota.com"
DOTA2_ABILITYLIST_URL = "https://www.dota2.com/datafeed/abilitylist"

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


def _load_official_ability_names(language: str = "schinese") -> Dict[str, Dict[str, str]]:
    """
    从 DOTA2 官方 API 加载技能名称映射
    
    Returns:
        {internal_name: {"name_loc": str, "name_english_loc": str}}
    """
    try:
        with httpx.Client(timeout=15.0, headers=DEFAULT_HEADERS) as client:
            resp = client.get(
                DOTA2_ABILITYLIST_URL,
                params={"language": language},
            )
            resp.raise_for_status()
            data = resp.json()
            abilities = data.get("result", {}).get("data", {}).get("itemabilities", [])
            
            # 建立 internal_name -> {name_loc, name_english_loc} 映射
            name_map = {}
            for ability in abilities:
                internal_name = ability.get("name", "")
                if internal_name:
                    name_map[internal_name] = {
                        "name_loc": ability.get("name_loc", ""),
                        "name_english_loc": ability.get("name_english_loc", ""),
                    }
            
            logger.info(f"已从官方 API 加载 {len(name_map)} 个技能名称映射")
            return name_map
    except Exception as e:
        logger.warning(f"从官方 API 加载技能名称失败: {e}")
        return {}


def fetch_abilities() -> List[Dict[str, Any]]:
    """
    从 OpenDota API 获取所有英雄的技能数据，并合并官方 API 的中文名称
    
    Returns:
        技能数据列表，每个技能包含名称、描述、数值等
    """
    logger.info("开始获取技能数据...")
    
    # 先加载官方 API 的中文名称映射
    official_names = _load_official_ability_names()
    
    with RateLimitedClient(OPENDOTA_BASE_URL) as client:
        # 获取技能常量数据
        abilities_response = client.get("/api/constants/abilities")
        abilities_data = abilities_response.json()
        
        # 获取神杖升级数据
        try:
            aghs_response = client.get("/api/constants/aghs_desc")
            aghs_data = aghs_response.json()
        except Exception:
            aghs_data = {}
        
        result = []
        for ability_key, ability_info in abilities_data.items():
            # 跳过非英雄技能（如天赋树等）
            if not isinstance(ability_info, dict):
                continue
            
            dname = ability_info.get("dname", "")
            if not dname:
                continue
            
            # 尝试从官方 API 获取中文名称
            official_name_info = official_names.get(ability_key, {})
            name_loc = official_name_info.get("name_loc", "")
            name_english_loc = official_name_info.get("name_english_loc", "")
            
            ability = {
                "key": ability_key,
                "name": dname,  # OpenDota 英文显示名
                "name_loc": name_loc,  # 官方 API 中文名
                "name_english_loc": name_english_loc or dname,  # 官方 API 英文名（降级到 OpenDota）
                "description": ability_info.get("desc", ""),
                "lore": ability_info.get("lore", ""),
                "behavior": ability_info.get("behavior", ""),
                "damage_type": ability_info.get("dmg_type", ""),
                "bkb_pierce": ability_info.get("bkbpierce", ""),
                "target_type": ability_info.get("target_team", ""),
                # 技能数值
                "cooldown": ability_info.get("cd", []),
                "mana_cost": ability_info.get("mc", []),
                "attributes": ability_info.get("attrib", []),
            }
            
            # 添加神杖/魔晶升级信息
            if ability_key in aghs_data:
                aghs_info = aghs_data[ability_key]
                if isinstance(aghs_info, dict):
                    ability["aghs_scepter"] = aghs_info.get("scepter_desc", "")
                    ability["aghs_shard"] = aghs_info.get("shard_desc", "")
            
            result.append(ability)
        
        logger.info(f"成功获取 {len(result)} 个技能的数据（其中 {sum(1 for a in result if a.get('name_loc'))} 个有中文名）")
        return result
