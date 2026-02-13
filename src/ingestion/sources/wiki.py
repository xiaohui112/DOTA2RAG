"""从 Dota 2 Wiki 爬取关键文章"""
import logging
import re
from typing import List, Dict, Any

from .http_client import RateLimitedClient

logger = logging.getLogger(__name__)

# Dota 2 Wiki（Liquipedia）API 端点
WIKI_BASE_URL = "https://liquipedia.net"

# Dota 2 Wiki 关键概念页面（使用 OpenDota 的 constants 作为替代数据源）
OPENDOTA_BASE_URL = "https://api.opendota.com"


def _clean_html(text: str) -> str:
    """简单去除 HTML 标签"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fetch_game_mechanics() -> List[Dict[str, Any]]:
    """
    从 OpenDota API 获取游戏机制相关常量数据
    
    Returns:
        游戏机制文档列表
    """
    logger.info("开始获取游戏机制数据...")
    
    mechanics_docs = []
    
    with RateLimitedClient(OPENDOTA_BASE_URL) as client:
        # 获取游戏常量
        constants_endpoints = {
            "game_mode": ("游戏模式", "/api/constants/game_mode"),
            "lobby_type": ("大厅类型", "/api/constants/lobby_type"),
            "region": ("服务器区域", "/api/constants/region"),
            "permanent_buffs": ("永久增益", "/api/constants/permanent_buffs"),
            "chat_wheel": ("聊天轮盘", "/api/constants/chat_wheel"),
        }
        
        for key, (name, endpoint) in constants_endpoints.items():
            try:
                response = client.get(endpoint)
                data = response.json()
                
                # 将常量数据转换为文档格式
                if isinstance(data, dict):
                    content_parts = [f"# {name}\n"]
                    for item_key, item_value in data.items():
                        if isinstance(item_value, dict):
                            item_name = item_value.get("name", item_value.get("dname", item_key))
                            content_parts.append(f"- {item_name}")
                        elif isinstance(item_value, str):
                            content_parts.append(f"- {item_key}: {item_value}")
                    
                    mechanics_docs.append({
                        "content": "\n".join(content_parts),
                        "metadata": {
                            "source": "api",
                            "category": "mechanic",
                            "entity_name": name,
                        },
                    })
                    
            except Exception as e:
                logger.warning(f"获取 {name} 数据失败: {e}")
    
    logger.info(f"成功获取 {len(mechanics_docs)} 个游戏机制文档")
    return mechanics_docs


def fetch_wiki() -> List[Dict[str, Any]]:
    """
    获取 Wiki 相关数据（使用 OpenDota 常量作为数据源）
    
    Returns:
        Wiki 文档列表
    """
    return fetch_game_mechanics()
