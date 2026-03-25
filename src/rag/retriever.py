"""查询预处理与多 Collection 检索"""
import logging
import math
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
    # 常见物品名称
    "希瓦", "shiva", "辉耀", "radiance", "深渊", "abyssal", "刃甲", "blade mail",
    "金箍棒", "monkey king bar", "大炮", "daedalus", "黑黄", "bkb", "跳刀", "blink",
    "紫苑", "kaya", "血精石", "bloodstone", "羊刀", "scythe", "hex",
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

    Returns:
        "zh" 或 "en"
    """
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())
    if total_chars == 0:
        return "en"
    return "zh" if chinese_chars / total_chars > 0.3 else "en"


def preprocess_query(query: str) -> str:
    """查询预处理：去除首尾空白、标准化空格"""
    query = query.strip()
    query = re.sub(r'\s+', ' ', query)
    return query


async def translate_query(query: str) -> str:
    """将中文查询翻译为英文（用于检索）"""
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

    Returns:
        版本号字符串，未检测到返回 None
    """
    # 匹配 X.YY[a-z]? 格式，兼容中文环境（不要求单词边界）
    match = re.search(r'(\d+\.\d{1,3}[a-z]?)', query)
    if match:
        return match.group(1)
    return None


def is_latest_version_query(query: str) -> bool:
    """
    检测用户是否在询问"最新版本"相关问题

    Returns:
        如果是询问最新版本则返回 True
    """
    query_lower = query.lower()
    latest_keywords = [
        "最新", "latest", "newest", "current", "现在", "当前",
        "new version", "新版本", "最近更新", "recent",
    ]
    return any(kw in query_lower for kw in latest_keywords)


def is_item_query(query: str) -> bool:
    """
    检测查询是否关于物品

    Returns:
        如果是物品查询则返回 True
    """
    query_lower = query.lower()
    return any(kw in query_lower for kw in ITEM_KEYWORDS)


def detect_collections(query: str) -> List[str]:
    """
    根据查询意图判断应搜索的 Collection

    Returns:
        Collection 名称列表
    """
    query_lower = query.lower()
    collections = set()

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

    # 没有匹配到任何关键词，搜索所有 Collection
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

    改进点：
    - 每个 Collection 按配额分配，确保所有 Collection 的结果都能被保留
    - 中文查询同时用原始中文和英文翻译双语检索，合并去重
    - 检测"最新版本"查询，按时间戳排序返回结果
    """
    # 1. 查询预处理
    processed_query = preprocess_query(query)

    # 检测是否在询问最新版本
    is_latest_query = is_latest_version_query(processed_query)

    # 检测是否是物品查询
    is_item = is_item_query(processed_query)

    # 2. 语言检测和翻译
    lang = detect_language(processed_query)
    translated_query: Optional[str] = None

    if lang == "zh" and enable_translation:
        translated_query = await translate_query(processed_query)

    # 3. 检测应搜索的 Collection（用原始 query，保留中英文关键词检测能力）
    target_collections = detect_collections(processed_query)

    # 4. 检测版本号（用于 patches 的 metadata 过滤）
    patch_version = detect_patch_version(processed_query)
    if patch_version:
        logger.info(f"检测到版本号: {patch_version}，将对 patches 进行精确过滤")
        if "patches" not in target_collections:
            target_collections.append("patches")

    logger.info(f"搜索 Collection: {target_collections}, 原始查询: '{processed_query}', 翻译查询: '{translated_query}'")

    # 5. 计算每个 Collection 的配额（均分，保证所有 Collection 都有结果）
    per_collection_quota = max(1, math.ceil(top_k / len(target_collections)))

    # 6. 多 Collection 检索
    all_results: List[Document] = []
    sources: List[Dict] = []
    seen_contents: set = set()  # 用于双语检索去重

    for collection in target_collections:
        try:
            count = vector_store.get_collection_count(collection)
            logger.info(f"[Retriever] Collection '{collection}' 文档数量: {count}")
            if count == 0:
                logger.warning(f"[Retriever] Collection '{collection}' 为空，跳过")
                continue

            filter_dict = None
            if collection == "patches":
                # 如果同时指定了版本号和物品查询，组合过滤
                if patch_version and is_item:
                    filter_dict = {
                        "$and": [
                            {"patch_version": patch_version},
                            {"change_category": "item"}
                        ]
                    }
                    logger.info(f"[Retriever] 检测到版本+物品查询，过滤 version={patch_version} AND category=item")
                # 如果只指定了版本号，过滤版本
                elif patch_version:
                    filter_dict = {"patch_version": patch_version}
                # 如果只是物品查询，优先搜索物品改动
                elif is_item:
                    filter_dict = {"change_category": "item"}
                    logger.info("[Retriever] 检测到物品查询，过滤 change_category=item")

            # 用于收集本 Collection 去重后的结果
            collection_docs: List[Document] = []
            collection_sources: List[Dict] = []

            # 特殊处理：如果是 patches collection 且用户在询问最新版本，直接获取最新补丁
            if collection == "patches" and is_latest_query and not patch_version:
                logger.info("[Retriever] 检测到最新版本查询，直接获取时间戳排序的最新补丁")
                docs = vector_store.get_latest_patches(top_k=per_collection_quota)
            else:
                # 5a. 原始查询检索
                primary_query = processed_query
                docs = vector_store.search(
                    collection=collection,
                    query=primary_query,
                    top_k=per_collection_quota,
                    filter_dict=filter_dict,
                )
            for doc in docs:
                key = doc.page_content[:200]
                if key not in seen_contents:
                    seen_contents.add(key)
                    collection_docs.append(doc)
                    collection_sources.append({
                        "collection": collection,
                        "entity_name": doc.metadata.get("entity_name", "unknown"),
                        "source": doc.metadata.get("source", "unknown"),
                        "category": doc.metadata.get("category", collection),
                    })

            # 5b. 双语检索：若有翻译且本 Collection 结果不足配额，补充英文查询结果
            if translated_query and translated_query != processed_query:
                remaining = per_collection_quota - len(collection_docs)
                if remaining > 0:
                    en_docs = vector_store.search(
                        collection=collection,
                        query=translated_query,
                        top_k=per_collection_quota,
                        filter_dict=filter_dict,
                    )
                    for doc in en_docs:
                        if len(collection_docs) >= per_collection_quota:
                            break
                        key = doc.page_content[:200]
                        if key not in seen_contents:
                            seen_contents.add(key)
                            collection_docs.append(doc)
                            collection_sources.append({
                                "collection": collection,
                                "entity_name": doc.metadata.get("entity_name", "unknown"),
                                "source": doc.metadata.get("source", "unknown"),
                                "category": doc.metadata.get("category", collection),
                            })

            logger.info(f"[Retriever] Collection '{collection}' 最终返回 {len(collection_docs)} 个文档")
            all_results.extend(collection_docs)
            sources.extend(collection_sources)

        except Exception as e:
            logger.warning(f"搜索 {collection} 失败: {e}", exc_info=True)

    logger.info(f"[Retriever] 检索完成，共 {len(all_results)} 个结果")
    if len(all_results) == 0:
        logger.warning("[Retriever] ⚠️ 检索结果为空！知识库可能没有相关数据或所有 Collection 为空")

    return all_results, sources
