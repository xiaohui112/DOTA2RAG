"""查询预处理与多 Collection 检索"""
import logging
import re
from typing import List, Dict, Optional, Tuple

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from config.settings import settings
from src.vectorstore.store import VectorStore

logger = logging.getLogger(__name__)

# 英雄相关关键词
HERO_KEYWORDS = [
    "英雄", "hero", "技能", "ability", "skill", "天赋", "talent",
    "敏捷", "力量", "智力", "agi", "str", "int", "属性", "attribute",
    "定位", "role", "carry", "support", "核心", "辅助", "打法",
]

# 物品相关关键词
ITEM_KEYWORDS = [
    "物品", "item", "装备", "equipment", "价格", "cost", "gold",
    "合成", "recipe", "效果", "effect", "主动", "被动", "active", "passive",
    "买", "出装", "build",
]

# 版本相关关键词
PATCH_KEYWORDS = [
    "版本", "patch", "更新", "update", "改动", "change", "buff", "nerf",
    "加强", "削弱", "重做", "rework", "新增",
]

# Wiki/机制相关关键词
WIKI_KEYWORDS = [
    "机制", "mechanic", "护甲", "armor", "伤害", "damage", "魔法",
    "物理", "纯粹", "pure", "减速", "stun", "眩晕", "沉默", "silence",
    "隐身", "invisible", "真视", "视野", "地图", "野怪", "roshan",
]


def detect_language(text: str) -> str:
    """
    检测文本语言（简单实现）
    
    Args:
        text: 输入文本
        
    Returns:
        "zh" 或 "en"
    """
    # 统计中文字符比例
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())
    if total_chars == 0:
        return "en"
    return "zh" if chinese_chars / total_chars > 0.3 else "en"


def preprocess_query(query: str) -> str:
    """
    查询预处理：去除首尾空白、标准化
    
    Args:
        query: 原始查询文本
        
    Returns:
        预处理后的查询文本
    """
    # 去除首尾空白
    query = query.strip()
    # 合并多余空白
    query = re.sub(r'\s+', ' ', query)
    return query


async def translate_query(query: str) -> str:
    """
    将中文查询翻译为英文（用于检索）
    
    Args:
        query: 中文查询
        
    Returns:
        英文查询
    """
    try:
        from src.rag.prompts import TRANSLATION_PROMPT
        
        llm = ChatOpenAI(
            model=settings.CHAT_MODEL,
            openai_api_key=settings.DASHSCOPE_API_KEY,
            openai_api_base=settings.API_BASE_URL,
            temperature=0.1,
            max_tokens=200,
        )
        
        prompt = TRANSLATION_PROMPT.format(query=query)
        result = await llm.ainvoke(prompt)
        translated = result.content.strip()
        logger.info(f"查询翻译: '{query}' -> '{translated}'")
        return translated
    except Exception as e:
        logger.warning(f"查询翻译失败，使用原始查询: {e}")
        return query


def detect_patch_version(query: str) -> Optional[str]:
    """
    从用户查询中提取 Dota 2 版本号（如 7.40c、7.38b 等）。

    Args:
        query: 用户查询

    Returns:
        版本号字符串，未检测到返回 None
    """
    # 匹配 7.xx 或 7.xxa/b/c/d/e 格式的版本号（兼容中文上下文）
    match = re.search(r'(7\.\d{2}[a-e]?)', query)
    if match:
        return match.group(1)
    return None


def detect_collections(query: str) -> List[str]:
    """
    根据查询意图判断应搜索的 Collection
    
    Args:
        query: 用户查询
        
    Returns:
        Collection 名称列表
    """
    query_lower = query.lower()
    collections = set()
    
    # 检测各类别关键词
    for kw in HERO_KEYWORDS:
        if kw in query_lower:
            collections.add("heroes")
            break
    
    for kw in ITEM_KEYWORDS:
        if kw in query_lower:
            collections.add("items")
            break
    
    for kw in PATCH_KEYWORDS:
        if kw in query_lower:
            collections.add("patches")
            break
    
    for kw in WIKI_KEYWORDS:
        if kw in query_lower:
            collections.add("wiki")
            break
    
    # 如果没有匹配到任何关键词，搜索所有 Collection
    if not collections:
        collections = {"heroes", "items", "patches", "wiki"}
    
    return list(collections)


async def retrieve(
    vector_store: VectorStore,
    query: str,
    top_k: int = 5,
    enable_translation: bool = True,
) -> Tuple[List[Document], List[Dict]]:
    """
    执行检索：查询预处理 -> 翻译（可选）-> 多 Collection 搜索 -> 合并排序
    
    Args:
        vector_store: 向量存储实例
        query: 用户查询
        top_k: 每个 Collection 返回的结果数
        enable_translation: 是否启用中文翻译
        
    Returns:
        (相关文档列表, 来源信息列表)
    """
    # 1. 查询预处理
    processed_query = preprocess_query(query)
    
    # 2. 语言检测和翻译
    lang = detect_language(processed_query)
    search_query = processed_query
    
    if lang == "zh" and enable_translation:
        search_query = await translate_query(processed_query)
    
    # 3. 检测应搜索的 Collection
    target_collections = detect_collections(processed_query)

    # 3.5 检测版本号（用于 patches 的 metadata 过滤）
    patch_version = detect_patch_version(processed_query)
    if patch_version:
        logger.info(f"检测到版本号: {patch_version}，将对 patches 进行精确过滤")
        if "patches" not in target_collections:
            target_collections.append("patches")

    logger.info(f"搜索 Collection: {target_collections}, 查询: '{search_query}'")
    
    # 4. 多 Collection 检索
    all_results = []
    sources = []
    
    for collection in target_collections:
        try:
            # 检查 Collection 是否有数据
            count = vector_store.get_collection_count(collection)
            logger.info(f"[Retriever] Collection '{collection}' 文档数量: {count}")
            if count == 0:
                logger.warning(f"[Retriever] Collection '{collection}' 为空，跳过")
                continue
            
            # 对 patches collection 应用版本号 metadata 过滤
            filter_dict = None
            if collection == "patches" and patch_version:
                filter_dict = {"patch_version": patch_version}

            docs = vector_store.search(
                collection=collection,
                query=search_query,
                top_k=top_k,
                filter_dict=filter_dict,
            )
            logger.info(f"[Retriever] Collection '{collection}' 返回 {len(docs)} 个文档")
            
            for doc in docs:
                all_results.append(doc)
                sources.append({
                    "collection": collection,
                    "entity_name": doc.metadata.get("entity_name", "unknown"),
                    "source": doc.metadata.get("source", "unknown"),
                    "category": doc.metadata.get("category", collection),
                })
                
        except Exception as e:
            logger.warning(f"搜索 {collection} 失败: {e}", exc_info=True)
    
    # 5. 按 top_k 截取总结果
    if len(all_results) > top_k:
        all_results = all_results[:top_k]
        sources = sources[:top_k]
    
    logger.info(f"[Retriever] 检索完成，共 {len(all_results)} 个结果, 截取前 {top_k} 个")
    if len(all_results) == 0:
        logger.warning("[Retriever] ⚠️ 检索结果为空！知识库可能没有相关数据或所有 Collection 为空")
    return all_results, sources
