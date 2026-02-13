"""数据源采集模块"""
from .heroes import fetch_heroes
from .items import fetch_items
from .abilities import fetch_abilities
from .patches import fetch_patches
from .wiki import fetch_wiki

__all__ = [
    "fetch_heroes",
    "fetch_items",
    "fetch_abilities",
    "fetch_patches",
    "fetch_wiki",
]
