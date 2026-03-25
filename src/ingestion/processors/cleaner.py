"""数据清洗和标准化处理"""
import re
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional
from html import unescape

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def clean_html(text: str) -> str:
    """
    去除 HTML 标签和实体
    
    Args:
        text: 原始文本
        
    Returns:
        清洗后的文本
    """
    if not text:
        return ""
    
    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(text, "lxml")
    # 获取纯文本
    cleaned = soup.get_text(separator=" ", strip=True)
    # 解码 HTML 实体
    cleaned = unescape(cleaned)
    return cleaned


def normalize_whitespace(text: str) -> str:
    """
    统一空白字符（多个空格/换行合并为单个空格）
    
    Args:
        text: 原始文本
        
    Returns:
        标准化后的文本
    """
    if not text:
        return ""
    
    # 将多个空白字符（空格、换行、制表符等）替换为单个空格
    normalized = re.sub(r"\s+", " ", text)
    return normalized.strip()


def normalize_number(value: Any) -> Optional[float]:
    """
    标准化数值格式
    
    Args:
        value: 原始值（可能是字符串、数字等）
        
    Returns:
        标准化后的浮点数，如果无法转换则返回 None
    """
    if value is None:
        return None
    
    try:
        # 尝试转换为浮点数
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # 去除可能的空格和特殊字符
            cleaned = value.strip().replace(",", "")
            return float(cleaned)
    except (ValueError, AttributeError):
        pass
    
    return None


def add_metadata(
    data: Dict[str, Any],
    source: str,
    category: str,
    entity_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    为数据添加元数据标签
    
    Args:
        data: 原始数据字典
        source: 数据来源（api/wiki/patch）
        category: 数据类别（hero/item/patch/mechanic）
        entity_name: 实体名称（如英雄名、物品名等）
        
    Returns:
        添加了元数据的数据字典
    """
    data["metadata"] = {
        "source": source,
        "category": category,
        "entity_name": entity_name or data.get("name", ""),
        "last_updated": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
    }
    return data
