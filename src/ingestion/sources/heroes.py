"""
从 Dota 2 官方 API 和 OpenDota API 获取完整的英雄数据

数据源：
  - 英雄列表: https://www.dota2.com/datafeed/herolist?language=schinese
  - 英雄详情: https://www.dota2.com/datafeed/herodata?language=schinese&hero_id=xxx
  - 英雄统计: https://api.opendota.com/api/heroStats
"""
import logging
import time
from typing import List, Dict, Any, Optional

import httpx

from .http_client import RateLimitedClient

logger = logging.getLogger(__name__)

# Dota 2 官方 API
DOTA2_HEROLIST_URL = "https://www.dota2.com/datafeed/herolist"
DOTA2_HERODATA_URL = "https://www.dota2.com/datafeed/herodata"

# OpenDota API
OPENDOTA_BASE_URL = "https://api.opendota.com"

# 默认请求头
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 技能快捷键映射（根据技能在数组中的位置）
ABILITY_HOTKEYS = ["Q", "W", "E", "R", "D", "F"]

# 英雄常用简称映射（手动维护）
HERO_NICKNAMES = {
    "npc_dota_hero_antimage": ["AM", "敌法", "敌法师"],
    "npc_dota_hero_axe": ["斧王", "AXE"],
    "npc_dota_hero_bane": ["祸乱之源", "祸乱"],
    "npc_dota_hero_bloodseeker": ["血魔", "BS"],
    "npc_dota_hero_crystal_maiden": ["冰女", "CM", "水晶室女"],
    "npc_dota_hero_drow_ranger": ["小黑", "DR", "卓尔游侠"],
    "npc_dota_hero_earthshaker": ["撼地者", "ES", "牛头"],
    "npc_dota_hero_juggernaut": ["剑圣", "JUGG", "主宰"],
    "npc_dota_hero_mirana": ["米拉娜", "POTM", "白虎"],
    "npc_dota_hero_morphling": ["水人", "MORPH", "变体精灵"],
    "npc_dota_hero_nevermore": ["影魔", "SF", "SF"],
    "npc_dota_hero_phantom_lancer": ["幻影长矛手", "PL", "猴子"],
    "npc_dota_hero_puck": ["帕克", "PUCK"],
    "npc_dota_hero_pudge": ["屠夫", "PUDGE", "胖子"],
    "npc_dota_hero_razor": ["电魂", "RAZOR", "剃刀"],
    "npc_dota_hero_sand_king": ["沙王", "SK"],
    "npc_dota_hero_storm_spirit": ["蓝猫", "SS", "风暴之灵"],
    "npc_dota_hero_sven": ["斯温", "SVEN"],
    "npc_dota_hero_tiny": ["小小", "TINY"],
    "npc_dota_hero_vengefulspirit": ["VS", "复仇之魂"],
    "npc_dota_hero_windrunner": ["风行", "WR", "风行者"],
    "npc_dota_hero_zuus": ["宙斯", "ZEUS"],
    "npc_dota_hero_kunkka": ["船长", "KUNKKA"],
    "npc_dota_hero_lina": ["火女", "LINA", "莉娜"],
    "npc_dota_hero_lich": ["巫妖", "LICH"],
    "npc_dota_hero_lion": ["莱恩", "LION", "恶魔巫师"],
    "npc_dota_hero_shadow_shaman": ["小Y", "SS", "暗影萨满"],
    "npc_dota_hero_slardar": ["大鱼", "SLARDAR", "斯拉达"],
    "npc_dota_hero_tidehunter": ["潮汐", "TH", "潮汐猎人"],
    "npc_dota_hero_witch_doctor": ["WD", "巫医"],
    "npc_dota_hero_lifestealer": ["小狗", "LS", "噬魂鬼"],
    "npc_dota_hero_riki": ["隐刺", "RIKI", "力丸"],
    "npc_dota_hero_enigma": ["谜团", "ENIGMA"],
    "npc_dota_hero_tinker": ["TK", "修补匠"],
    "npc_dota_hero_sniper": ["火枪", "SNIPER", "矮人狙击手"],
    "npc_dota_hero_necrolyte": ["死灵法", "NEC", "死灵法师"],
    "npc_dota_hero_warlock": ["WL", "术士"],
    "npc_dota_hero_beastmaster": ["BM", "兽王"],
    "npc_dota_hero_queenofpain": ["QOP", "痛苦女王"],
    "npc_dota_hero_venomancer": ["剧毒", "VENO", "剧毒术士"],
    "npc_dota_hero_faceless_void": ["虚空", "FV", "虚空假面"],
    "npc_dota_hero_skeleton_king": ["骷髅王", "SK", "冥魂大帝"],
    "npc_dota_hero_death_prophet": ["DP", "死亡先知"],
    "npc_dota_hero_phantom_assassin": ["PA", "幻影刺客"],
    "npc_dota_hero_pugna": ["骨法", "PUGNA", "帕格纳"],
    "npc_dota_hero_templar_assassin": ["TA", "圣堂刺客"],
    "npc_dota_hero_viper": ["毒龙", "VIPER", "冥界亚龙"],
    "npc_dota_hero_luna": ["月骑", "LUNA", "露娜"],
    "npc_dota_hero_dragon_knight": ["DK", "龙骑"],
    "npc_dota_hero_dazzle": ["暗牧", "DAZZLE", "戴泽"],
    "npc_dota_hero_rattletrap": ["发条", "CLOCK", "发条技师"],
    "npc_dota_hero_leshrac": ["TS", "拉席克"],
    "npc_dota_hero_furion": ["先知", "NP", "自然先知"],
    "npc_dota_hero_life_stealer": ["小狗", "LS", "噬魂鬼"],
    "npc_dota_hero_dark_seer": ["DS", "黑暗贤者"],
    "npc_dota_hero_clinkz": ["骨弓", "CLINKZ", "克林克兹"],
    "npc_dota_hero_omniknight": ["全能", "OMNI", "全能骑士"],
    "npc_dota_hero_enchantress": ["小鹿", "ENCH", "魅惑魔女"],
    "npc_dota_hero_huskar": ["哈斯卡", "HUSKAR"],
    "npc_dota_hero_night_stalker": ["夜魔", "NS", "暗夜魔王"],
    "npc_dota_hero_broodmother": ["蜘蛛", "BM", "育母蜘蛛"],
    "npc_dota_hero_bounty_hunter": ["BH", "赏金猎人"],
    "npc_dota_hero_weaver": ["蚂蚁", "WEAVER", "编织者"],
    "npc_dota_hero_jakiro": ["双头龙", "JAKIRO"],
    "npc_dota_hero_batrider": ["蝙蝠", "BAT", "蝙蝠骑士"],
    "npc_dota_hero_chen": ["陈", "CHEN"],
    "npc_dota_hero_spectre": ["幽鬼", "SPEC", "幽鬼"],
    "npc_dota_hero_doom_bringer": ["DOOM", "末日使者"],
    "npc_dota_hero_ancient_apparition": ["冰魂", "AA", "远古冰魄"],
    "npc_dota_hero_ursa": ["拍拍", "URSA", "熊战士"],
    "npc_dota_hero_spirit_breaker": ["白牛", "SB", "裂魂人"],
    "npc_dota_hero_gyrocopter": ["飞机", "GYRO", "矮人直升机"],
    "npc_dota_hero_alchemist": ["炼金", "ALCH", "炼金术士"],
    "npc_dota_hero_invoker": ["卡尔", "INVOKER", "祈求者"],
    "npc_dota_hero_silencer": ["沉默", "SIL", "沉默术士"],
    "npc_dota_hero_obsidian_destroyer": ["黑鸟", "OD", "殁境神蚀者"],
    "npc_dota_hero_lycan": ["狼人", "LYCAN"],
    "npc_dota_hero_brewmaster": ["熊猫", "BREW", "酒仙"],
    "npc_dota_hero_shadow_demon": ["毒狗", "SD", "暗影恶魔"],
    "npc_dota_hero_lone_druid": ["德鲁伊", "LD", "德鲁伊"],
    "npc_dota_hero_chaos_knight": ["CK", "混沌骑士"],
    "npc_dota_hero_meepo": ["米波", "MEEPO"],
    "npc_dota_hero_treant": ["大树", "TREANT", "树精卫士"],
    "npc_dota_hero_ogre_magi": ["蓝胖", "OGRE", "食人魔魔法师"],
    "npc_dota_hero_undying": ["尸王", "UNDYING", "不朽尸王"],
    "npc_dota_hero_rubick": ["拉比克", "RUBICK"],
    "npc_dota_hero_disruptor": ["萨尔", "DISRUPTOR", "干扰者"],
    "npc_dota_hero_nyx_assassin": ["小强", "NYX", "司夜刺客"],
    "npc_dota_hero_naga_siren": ["小娜迦", "NAGA", "娜迦海妖"],
    "npc_dota_hero_keeper_of_the_light": ["光法", "KOTL", "光之守卫"],
    "npc_dota_hero_io": ["小精灵", "IO", "艾欧"],
    "npc_dota_hero_visage": ["维萨吉", "VISAGE", "死灵飞龙"],
    "npc_dota_hero_slark": ["小鱼", "SLARK", "斯拉克"],
    "npc_dota_hero_medusa": ["美杜莎", "MEDUSA", "蛇发女妖"],
    "npc_dota_hero_troll_warlord": ["巨魔", "TROLL", "巨魔战将"],
    "npc_dota_hero_centaur": ["人马", "CENTAUR", "半人马战行者"],
    "npc_dota_hero_magnataur": ["猛犸", "MAG", "半人马战行者"],
    "npc_dota_hero_shredder": ["伐木机", "SHREDDER", "伐木机"],
    "npc_dota_hero_bristleback": ["刚背", "BB", "钢背兽"],
    "npc_dota_hero_tusk": ["海民", "TUSK", "巨牙海民"],
    "npc_dota_hero_skywrath_mage": ["天怒", "SKY", "天怒法师"],
    "npc_dota_hero_abaddon": ["亚巴顿", "ABADDON", "亚巴顿"],
    "npc_dota_hero_elder_titan": ["大牛", "ET", "上古巨神"],
    "npc_dota_hero_legion_commander": ["军团", "LC", "军团指挥官"],
    "npc_dota_hero_techies": ["炸弹人", "TECHIES", "工程师"],
    "npc_dota_hero_ember_spirit": ["火猫", "EMBER", "灰烬之灵"],
    "npc_dota_hero_earth_spirit": ["土猫", "EARTH", "大地之灵"],
    "npc_dota_hero_abyssal_underlord": ["大屁股", "UNDERLORD", "孽主"],
    "npc_dota_hero_terrorblade": ["TB", "恐怖利刃"],
    "npc_dota_hero_phoenix": ["凤凰", "PHOENIX"],
    "npc_dota_hero_oracle": ["神谕", "ORACLE", "神谕者"],
    "npc_dota_hero_winter_wyvern": ["冰龙", "WW", "寒冬飞龙"],
    "npc_dota_hero_arc_warden": ["电狗", "ARC", "天穹守望者"],
    "npc_dota_hero_monkey_king": ["大圣", "MK", "齐天大圣"],
    "npc_dota_hero_pangolier": ["滚滚", "PANGOLIER", "石鳞剑士"],
    "npc_dota_hero_dark_willow": ["小仙女", "DW", "邪影芳灵"],
    "npc_dota_hero_grimstroke": ["墨客", "GRIM", "天涯墨客"],
    "npc_dota_hero_mars": ["玛尔斯", "MARS", "玛尔斯"],
    "npc_dota_hero_snapfire": ["老奶奶", "SNAP", "电炎绝手"],
    "npc_dota_hero_void_spirit": ["紫猫", "VOID", "虚无之灵"],
    "npc_dota_hero_hoodwink": ["小松鼠", "HOOD", "森海飞霞"],
    "npc_dota_hero_dawnbreaker": ["破晓", "DAWN", "破晓辰星"],
    "npc_dota_hero_marci": ["玛西", "MARCI", "玛西"],
    "npc_dota_hero_primal_beast": ["兽", "PB", "兽"],
    "npc_dota_hero_muerta": ["墨影", "MUERTA", "墨影"],
}


def _fetch_hero_list(language: str = "schinese") -> List[Dict[str, Any]]:
    """
    从 Dota 2 官方 API 获取英雄列表
    
    Args:
        language: 语言代码，默认为 schinese（简体中文）
    
    Returns:
        英雄列表，每个英雄包含 id, name, name_loc, name_english_loc 等基础信息
    """
    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            resp = client.get(
                DOTA2_HEROLIST_URL,
                params={"language": language},
                headers={
                    **DEFAULT_HEADERS,
                    "referer": "https://www.dota2.com/heroes",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            
            heroes = data.get("result", {}).get("data", {}).get("heroes", [])
            logger.info(f"从官方 API 获取到 {len(heroes)} 个英雄的基础信息")
            return heroes
            
    except Exception as e:
        logger.error(f"获取英雄列表失败: {e}")
        return []


def _fetch_hero_detail(hero_id: int, language: str = "schinese") -> Optional[Dict[str, Any]]:
    """
    从 Dota 2 官方 API 获取单个英雄的详细信息（包括技能）
    
    Args:
        hero_id: 英雄ID
        language: 语言代码，默认为 schinese
    
    Returns:
        英雄详细信息，包含技能、属性等
    """
    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            resp = client.get(
                DOTA2_HERODATA_URL,
                params={"language": language, "hero_id": hero_id},
                headers={
                    **DEFAULT_HEADERS,
                    "referer": f"https://www.dota2.com/heroes",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            
            heroes = data.get("result", {}).get("data", {}).get("heroes", [])
            if heroes:
                return heroes[0]
            return None
            
    except Exception as e:
        logger.warning(f"获取英雄 {hero_id} 详细信息失败: {e}")
        return None


def _get_ability_hotkey(ability_index: int) -> str:
    """
    根据技能在数组中的位置获取快捷键
    
    Args:
        ability_index: 技能在数组中的索引
    
    Returns:
        快捷键（Q, W, E, R, D, F）
    """
    if ability_index < len(ABILITY_HOTKEYS):
        return ABILITY_HOTKEYS[ability_index]
    return ""


def _process_abilities(abilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    处理技能数据，添加快捷键和整理信息
    
    Args:
        abilities: 原始技能数据列表
    
    Returns:
        处理后的技能列表
    """
    processed = []
    
    for idx, ability in enumerate(abilities):
        # 跳过非英雄技能（物品技能等）
        if ability.get("is_item", False):
            continue
        
        # 获取技能简称（从技能名称中提取）
        ability_name = ability.get("name", "")
        ability_short_name = ""
        if ability_name:
            # 提取技能名称的最后部分作为简称
            parts = ability_name.split("_")
            if len(parts) > 0:
                ability_short_name = parts[-1].upper()
        
        processed_ability = {
            "id": ability.get("id"),
            "name": ability_name,
            "name_loc": ability.get("name_loc", ""),  # 中文名
            "name_english_loc": ability.get("name_english_loc", ""),  # 英文名
            "short_name": ability_short_name,  # 简称
            "hotkey": _get_ability_hotkey(idx),  # 快捷键
            "description": ability.get("desc_loc", ""),  # 技能描述
            "lore": ability.get("lore_loc", ""),  # 背景故事
            "notes": ability.get("notes_loc", []),  # 技能说明
            "type": ability.get("type", 0),
            "behavior": ability.get("behavior", ""),
            "max_level": ability.get("max_level", 0),
            # 技能数值
            "cooldowns": ability.get("cooldowns", []),
            "mana_costs": ability.get("mana_costs", []),
            "cast_ranges": ability.get("cast_ranges", []),
            "cast_points": ability.get("cast_points", []),
            "durations": ability.get("durations", []),
            "damages": ability.get("damages", []),
            # 特殊数值
            "special_values": ability.get("special_values", []),
            # 神杖/魔晶升级
            "scepter_loc": ability.get("scepter_loc", ""),
            "shard_loc": ability.get("shard_loc", ""),
            "ability_has_scepter": ability.get("ability_has_scepter", False),
            "ability_has_shard": ability.get("ability_has_shard", False),
        }
        
        processed.append(processed_ability)
    
    return processed


def _get_hero_nicknames(hero_name: str) -> List[str]:
    """
    获取英雄的常用简称列表
    
    Args:
        hero_name: 英雄内部名称（如 npc_dota_hero_antimage）
    
    Returns:
        简称列表
    """
    return HERO_NICKNAMES.get(hero_name, [])


# 英雄上线版本映射（部分英雄，可根据需要补充）
HERO_RELEASE_VERSIONS = {
    # 原始英雄（Dota 1时代就有，Dota 2正式上线时已存在）
    "npc_dota_hero_antimage": "6.00",  # 敌法师
    "npc_dota_hero_axe": "6.00",  # 斧王
    "npc_dota_hero_bane": "6.00",  # 祸乱之源
    "npc_dota_hero_bloodseeker": "6.00",  # 血魔
    "npc_dota_hero_crystal_maiden": "6.00",  # 冰女
    "npc_dota_hero_drow_ranger": "6.00",  # 小黑
    "npc_dota_hero_earthshaker": "6.00",  # 撼地者
    "npc_dota_hero_juggernaut": "6.00",  # 剑圣
    "npc_dota_hero_mirana": "6.00",  # 米拉娜
    "npc_dota_hero_morphling": "6.00",  # 水人
    "npc_dota_hero_nevermore": "6.00",  # 影魔
    "npc_dota_hero_phantom_lancer": "6.00",  # 幻影长矛手
    "npc_dota_hero_puck": "6.00",  # 帕克
    "npc_dota_hero_pudge": "6.00",  # 屠夫
    "npc_dota_hero_razor": "6.00",  # 电魂
    "npc_dota_hero_sand_king": "6.00",  # 沙王
    "npc_dota_hero_storm_spirit": "6.00",  # 蓝猫
    "npc_dota_hero_sven": "6.00",  # 斯温
    "npc_dota_hero_tiny": "6.00",  # 小小
    "npc_dota_hero_vengefulspirit": "6.00",  # VS
    "npc_dota_hero_windrunner": "6.00",  # 风行
    "npc_dota_hero_zuus": "6.00",  # 宙斯
    "npc_dota_hero_kunkka": "6.00",  # 船长
    "npc_dota_hero_lina": "6.00",  # 火女
    "npc_dota_hero_lich": "6.00",  # 巫妖
    "npc_dota_hero_lion": "6.00",  # 莱恩
    "npc_dota_hero_shadow_shaman": "6.00",  # 小Y
    "npc_dota_hero_slardar": "6.00",  # 大鱼
    "npc_dota_hero_tidehunter": "6.00",  # 潮汐
    "npc_dota_hero_witch_doctor": "6.00",  # 巫医
    "npc_dota_hero_lifestealer": "6.00",  # 小狗
    "npc_dota_hero_riki": "6.00",  # 隐刺
    "npc_dota_hero_enigma": "6.00",  # 谜团
    "npc_dota_hero_tinker": "6.00",  # TK
    "npc_dota_hero_sniper": "6.00",  # 火枪
    "npc_dota_hero_necrolyte": "6.00",  # 死灵法
    "npc_dota_hero_warlock": "6.00",  # 术士
    "npc_dota_hero_beastmaster": "6.00",  # BM
    "npc_dota_hero_queenofpain": "6.00",  # QOP
    "npc_dota_hero_venomancer": "6.00",  # 剧毒
    "npc_dota_hero_faceless_void": "6.00",  # 虚空
    "npc_dota_hero_skeleton_king": "6.00",  # 骷髅王
    "npc_dota_hero_death_prophet": "6.00",  # DP
    "npc_dota_hero_phantom_assassin": "6.00",  # PA
    "npc_dota_hero_pugna": "6.00",  # 骨法
    "npc_dota_hero_templar_assassin": "6.00",  # TA
    "npc_dota_hero_viper": "6.00",  # 毒龙
    "npc_dota_hero_luna": "6.00",  # 月骑
    "npc_dota_hero_dragon_knight": "6.00",  # DK
    "npc_dota_hero_dazzle": "6.00",  # 暗牧
    "npc_dota_hero_rattletrap": "6.00",  # 发条
    "npc_dota_hero_leshrac": "6.00",  # TS
    "npc_dota_hero_furion": "6.00",  # 先知
    "npc_dota_hero_dark_seer": "6.00",  # DS
    "npc_dota_hero_clinkz": "6.00",  # 骨弓
    "npc_dota_hero_omniknight": "6.00",  # 全能
    "npc_dota_hero_enchantress": "6.00",  # 小鹿
    "npc_dota_hero_huskar": "6.00",  # 哈斯卡
    "npc_dota_hero_night_stalker": "6.00",  # 夜魔
    "npc_dota_hero_broodmother": "6.00",  # 蜘蛛
    "npc_dota_hero_bounty_hunter": "6.00",  # BH
    "npc_dota_hero_weaver": "6.00",  # 蚂蚁
    "npc_dota_hero_jakiro": "6.00",  # 双头龙
    "npc_dota_hero_batrider": "6.00",  # 蝙蝠
    "npc_dota_hero_chen": "6.00",  # 陈
    "npc_dota_hero_spectre": "6.00",  # 幽鬼
    "npc_dota_hero_doom_bringer": "6.00",  # DOOM
    "npc_dota_hero_ancient_apparition": "6.00",  # 冰魂
    "npc_dota_hero_ursa": "6.00",  # 拍拍
    "npc_dota_hero_spirit_breaker": "6.00",  # 白牛
    "npc_dota_hero_gyrocopter": "6.00",  # 飞机
    "npc_dota_hero_alchemist": "6.00",  # 炼金
    "npc_dota_hero_invoker": "6.00",  # 卡尔
    "npc_dota_hero_silencer": "6.00",  # 沉默
    "npc_dota_hero_obsidian_destroyer": "6.00",  # 黑鸟
    "npc_dota_hero_lycan": "6.00",  # 狼人
    "npc_dota_hero_brewmaster": "6.00",  # 熊猫
    "npc_dota_hero_shadow_demon": "6.00",  # 毒狗
    "npc_dota_hero_lone_druid": "6.00",  # 德鲁伊
    "npc_dota_hero_chaos_knight": "6.00",  # CK
    "npc_dota_hero_meepo": "6.00",  # 米波
    "npc_dota_hero_treant": "6.00",  # 大树
    "npc_dota_hero_ogre_magi": "6.00",  # 蓝胖
    "npc_dota_hero_undying": "6.00",  # 尸王
    "npc_dota_hero_rubick": "6.00",  # 拉比克
    "npc_dota_hero_disruptor": "6.00",  # 萨尔
    "npc_dota_hero_nyx_assassin": "6.00",  # 小强
    "npc_dota_hero_naga_siren": "6.00",  # 小娜迦
    "npc_dota_hero_keeper_of_the_light": "6.00",  # 光法
    "npc_dota_hero_io": "6.00",  # 小精灵
    "npc_dota_hero_visage": "6.00",  # 维萨吉
    "npc_dota_hero_slark": "6.00",  # 小鱼
    "npc_dota_hero_medusa": "6.00",  # 美杜莎
    "npc_dota_hero_troll_warlord": "6.00",  # 巨魔
    "npc_dota_hero_centaur": "6.00",  # 人马
    "npc_dota_hero_magnataur": "6.00",  # 猛犸
    "npc_dota_hero_shredder": "6.00",  # 伐木机
    "npc_dota_hero_bristleback": "6.00",  # 刚背
    "npc_dota_hero_tusk": "6.00",  # 海民
    "npc_dota_hero_skywrath_mage": "6.00",  # 天怒
    "npc_dota_hero_abaddon": "6.00",  # 亚巴顿
    "npc_dota_hero_elder_titan": "6.00",  # 大牛
    "npc_dota_hero_legion_commander": "6.00",  # 军团
    "npc_dota_hero_techies": "6.00",  # 炸弹人
    "npc_dota_hero_ember_spirit": "6.00",  # 火猫
    "npc_dota_hero_earth_spirit": "6.00",  # 土猫
    "npc_dota_hero_abyssal_underlord": "6.00",  # 大屁股
    "npc_dota_hero_terrorblade": "6.00",  # TB
    "npc_dota_hero_phoenix": "6.00",  # 凤凰
    "npc_dota_hero_oracle": "6.00",  # 神谕
    "npc_dota_hero_winter_wyvern": "6.00",  # 冰龙
    "npc_dota_hero_arc_warden": "6.00",  # 电狗
    "npc_dota_hero_monkey_king": "6.00",  # 大圣
    "npc_dota_hero_pangolier": "6.00",  # 滚滚
    "npc_dota_hero_dark_willow": "6.00",  # 小仙女
    "npc_dota_hero_grimstroke": "6.00",  # 墨客
    "npc_dota_hero_mars": "6.00",  # 玛尔斯
    "npc_dota_hero_snapfire": "6.00",  # 老奶奶
    "npc_dota_hero_void_spirit": "6.00",  # 紫猫
    "npc_dota_hero_hoodwink": "6.00",  # 小松鼠
    "npc_dota_hero_dawnbreaker": "6.00",  # 破晓
    "npc_dota_hero_marci": "6.00",  # 玛西
    "npc_dota_hero_primal_beast": "6.00",  # 兽
    "npc_dota_hero_muerta": "6.00",  # 墨影
    # 注意：以上版本号是近似值，实际需要从补丁记录中查找
    # 新英雄的上线版本可以通过遍历补丁记录查找"新增英雄"相关的内容来确定
}


def _find_hero_release_version(hero_name: str) -> Optional[str]:
    """
    查找英雄的上线版本
    
    优先从映射表中查找，如果找不到则返回None。
    如果需要更精确的版本，可以遍历补丁记录查找英雄首次出现的版本。
    
    Args:
        hero_name: 英雄内部名称
    
    Returns:
        上线版本号，如果找不到则返回None
    """
    # 从映射表中查找
    version = HERO_RELEASE_VERSIONS.get(hero_name)
    if version:
        return version
    
    # TODO: 如果需要更精确的版本，可以从补丁记录中查找
    # 实现方式：
    # 1. 获取所有补丁记录
    # 2. 遍历补丁记录，查找包含"新增英雄"或英雄名称首次出现的版本
    # 3. 返回找到的第一个版本号
    
    return None


def fetch_heroes(language: str = "schinese", include_details: bool = True) -> List[Dict[str, Any]]:
    """
    获取所有英雄的完整数据
    
    Args:
        language: 语言代码，默认为 schinese
        include_details: 是否获取详细信息（包括技能），默认为True
    
    Returns:
        英雄数据列表，每个英雄包含：
        - 基础信息：id, name, name_loc, name_english_loc, nicknames
        - 属性信息：基础属性、成长值、攻击力、护甲等
        - 技能信息：技能列表（包含快捷键、描述、数值等）
        - 上线版本：release_version（如果可找到）
    """
    logger.info("开始获取英雄数据...")
    
    # 1. 获取英雄列表
    hero_list = _fetch_hero_list(language)
    if not hero_list:
        logger.warning("未获取到英雄列表")
        return []
    
    # 2. 获取OpenDota的统计信息（用于补充属性数据）
    opendota_stats = {}
    try:
        with RateLimitedClient(OPENDOTA_BASE_URL) as client:
            stats_response = client.get("/api/heroStats")
            stats = stats_response.json()
            opendota_stats = {hero["id"]: hero for hero in stats}
            logger.info(f"从 OpenDota 获取到 {len(opendota_stats)} 个英雄的统计信息")
    except Exception as e:
        logger.warning(f"从 OpenDota 获取统计信息失败: {e}")
    
    # 3. 获取每个英雄的详细信息
    result = []
    total = len(hero_list)
    
    for idx, hero_basic in enumerate(hero_list):
        hero_id = hero_basic.get("id")
        hero_name = hero_basic.get("name", "")
        
        logger.info(f"处理英雄进度: {idx + 1}/{total} - {hero_basic.get('name_loc', hero_name)}")
        
        # 获取详细信息
        hero_detail = None
        if include_details:
            hero_detail = _fetch_hero_detail(hero_id, language)
            # 添加请求间隔，避免频率过高
            if idx < total - 1:
                time.sleep(0.5)
        
        # 合并数据
        hero_data = {
            # 基础信息
            "id": hero_id,
            "name": hero_name,
            "name_loc": hero_basic.get("name_loc", ""),  # 中文名
            "name_english_loc": hero_basic.get("name_english_loc", ""),  # 英文名
            "nicknames": _get_hero_nicknames(hero_name),  # 常用简称
            "release_version": _find_hero_release_version(hero_name),  # 上线版本
            
            # 从详细信息中获取的属性
            "bio": hero_detail.get("bio_loc", "") if hero_detail else "",
            "hype": hero_detail.get("hype_loc", "") if hero_detail else "",
            "complexity": hero_basic.get("complexity", 0),
            "primary_attr": hero_basic.get("primary_attr", 0),
            
            # 基础属性（优先使用详细信息，降级到基础信息）
            "str_base": hero_detail.get("str_base") if hero_detail else None,
            "str_gain": hero_detail.get("str_gain") if hero_detail else None,
            "agi_base": hero_detail.get("agi_base") if hero_detail else None,
            "agi_gain": hero_detail.get("agi_gain") if hero_detail else None,
            "int_base": hero_detail.get("int_base") if hero_detail else None,
            "int_gain": hero_detail.get("int_gain") if hero_detail else None,
            
            # 战斗属性
            "damage_min": hero_detail.get("damage_min") if hero_detail else None,
            "damage_max": hero_detail.get("damage_max") if hero_detail else None,
            "attack_range": hero_detail.get("attack_range") if hero_detail else None,
            "attack_rate": hero_detail.get("attack_rate") if hero_detail else None,
            "projectile_speed": hero_detail.get("projectile_speed") if hero_detail else None,
            "armor": hero_detail.get("armor") if hero_detail else None,
            "magic_resistance": hero_detail.get("magic_resistance") if hero_detail else None,
            "movement_speed": hero_detail.get("movement_speed") if hero_detail else None,
            "turn_rate": hero_detail.get("turn_rate") if hero_detail else None,
            
            # 生命值和魔法值
            "max_health": hero_detail.get("max_health") if hero_detail else None,
            "health_regen": hero_detail.get("health_regen") if hero_detail else None,
            "max_mana": hero_detail.get("max_mana") if hero_detail else None,
            "mana_regen": hero_detail.get("mana_regen") if hero_detail else None,
            
            # 视野
            "sight_range_day": hero_detail.get("sight_range_day") if hero_detail else None,
            "sight_range_night": hero_detail.get("sight_range_night") if hero_detail else None,
            
            # 技能列表
            "abilities": _process_abilities(hero_detail.get("abilities", [])) if hero_detail else [],
            
            # 天赋/面位（Facets）
            "facets": hero_detail.get("facets", []) if hero_detail else [],
        }
        
        # 从OpenDota补充缺失的属性
        opendota_hero = opendota_stats.get(hero_id, {})
        if opendota_hero:
            if hero_data["str_base"] is None:
                hero_data["str_base"] = opendota_hero.get("base_str")
            if hero_data["str_gain"] is None:
                hero_data["str_gain"] = opendota_hero.get("str_gain")
            if hero_data["agi_base"] is None:
                hero_data["agi_base"] = opendota_hero.get("base_agi")
            if hero_data["agi_gain"] is None:
                hero_data["agi_gain"] = opendota_hero.get("agi_gain")
            if hero_data["int_base"] is None:
                hero_data["int_base"] = opendota_hero.get("base_int")
            if hero_data["int_gain"] is None:
                hero_data["int_gain"] = opendota_hero.get("int_gain")
            
            # 补充其他属性
            if hero_data["attack_range"] is None:
                hero_data["attack_range"] = opendota_hero.get("attack_range")
            if hero_data["movement_speed"] is None:
                hero_data["movement_speed"] = opendota_hero.get("move_speed")
            if hero_data["sight_range_day"] is None:
                hero_data["sight_range_day"] = opendota_hero.get("day_vision")
            if hero_data["sight_range_night"] is None:
                hero_data["sight_range_night"] = opendota_hero.get("night_vision")
        
        result.append(hero_data)
    
    logger.info(f"成功获取 {len(result)} 个英雄的完整数据")
    return result
