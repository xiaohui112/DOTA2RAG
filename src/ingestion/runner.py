"""数据采集 CLI 入口"""
import argparse
import logging
import sys
import time
from typing import List, Dict, Any

from src.ingestion.sources.heroes import fetch_heroes
from src.ingestion.sources.items import fetch_items
from src.ingestion.sources.abilities import fetch_abilities
from src.ingestion.sources.patches import fetch_patches
from src.ingestion.sources.wiki import fetch_wiki
from src.ingestion.processors.cleaner import add_metadata, clean_html, normalize_whitespace
from src.ingestion.processors.chunker import chunk_hero_item, chunk_patch_notes, chunk_wiki_article
from src.ingestion.version_tracker import VersionTracker
from src.vectorstore.store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def ingest_heroes(vector_store: VectorStore) -> int:
    """采集并存储英雄数据"""
    logger.info("=== 开始采集英雄数据 ===")
    heroes = fetch_heroes()

    all_chunks = []
    for hero in heroes:
        hero_with_meta = add_metadata(
            hero, "api", "hero",
            hero.get("localized_name", hero.get("name", ""))
        )
        chunks = chunk_hero_item(hero_with_meta, "hero")
        all_chunks.extend(chunks)

    if all_chunks:
        vector_store.upsert_documents("heroes", all_chunks)

    logger.info(f"英雄数据采集完成: {len(heroes)} 个英雄, {len(all_chunks)} 个文档块")
    return len(all_chunks)


def ingest_items(vector_store: VectorStore) -> int:
    """采集并存储物品数据"""
    logger.info("=== 开始采集物品数据 ===")
    items = fetch_items()

    all_chunks = []
    for item in items:
        # 兼容官方 API 和 OpenDota API 的数据格式
        item_name = (
            item.get("name_loc") or  # 官方 API 中文名
            item.get("dname") or  # OpenDota API 显示名
            item.get("name_english_loc") or  # 官方 API 英文名
            item.get("name", "unknown")  # 通用名称字段
        )
        item_with_meta = add_metadata(
            item, "api", "item",
            item_name
        )
        chunks = chunk_hero_item(item_with_meta, "item")
        all_chunks.extend(chunks)

    if all_chunks:
        vector_store.upsert_documents("items", all_chunks)

    logger.info(f"物品数据采集完成: {len(items)} 个物品, {len(all_chunks)} 个文档块")
    return len(all_chunks)


def ingest_abilities(vector_store: VectorStore) -> int:
    """采集并存储技能数据（合并到 heroes Collection）"""
    logger.info("=== 开始采集技能数据 ===")
    abilities = fetch_abilities()

    all_chunks = []
    for ability in abilities:
        # 兼容官方 API 和 OpenDota API 的数据格式
        ability_name = (
            ability.get("name_loc") or  # 官方 API 中文名
            ability.get("name") or  # OpenDota API 显示名
            ability.get("name_english_loc") or  # 官方 API 英文名
            ability.get("key", "unknown")  # 通用名称字段
        )
        
        # 构建技能文档内容
        content_parts = [
            f"技能名称: {ability_name}",
            f"描述: {ability.get('description', '')}",
        ]

        if ability.get("cooldown"):
            content_parts.append(f"冷却时间: {ability['cooldown']}")
        if ability.get("mana_cost"):
            content_parts.append(f"魔耗: {ability['mana_cost']}")
        if ability.get("damage_type"):
            content_parts.append(f"伤害类型: {ability['damage_type']}")
        if ability.get("aghs_scepter"):
            content_parts.append(f"阿哈利姆神杖升级: {ability['aghs_scepter']}")
        if ability.get("aghs_shard"):
            content_parts.append(f"阿哈利姆魔晶升级: {ability['aghs_shard']}")

        doc = {
            "content": "\n".join(content_parts),
            "metadata": {
                "source": "api",
                "category": "ability",
                "entity_name": ability_name,
            },
        }
        all_chunks.append(doc)

    if all_chunks:
        vector_store.upsert_documents("heroes", all_chunks)

    logger.info(f"技能数据采集完成: {len(abilities)} 个技能, {len(all_chunks)} 个文档块")
    return len(all_chunks)


def ingest_patches(
    vector_store: VectorStore,
    since_version: str = None,
) -> tuple:
    """
    采集并存储 Patch Notes（使用新的分块策略）

    Returns:
        (文档块数量, 最新版本号)
    """
    logger.info("=== 开始采集 Patch Notes ===")
    patches = fetch_patches(since_version=since_version)

    all_chunks = []
    for patch in patches:
        chunks = chunk_patch_notes(patch)
        all_chunks.extend(chunks)

    if all_chunks:
        vector_store.upsert_documents("patches", all_chunks)

    # 找出最新版本号
    latest_patch = ""
    if patches:
        latest_patch = patches[-1].get("name", "")

    logger.info(
        f"Patch Notes 采集完成: {len(patches)} 个版本, "
        f"{len(all_chunks)} 个文档块, 最新版本: {latest_patch}"
    )
    return len(all_chunks), latest_patch


def ingest_wiki(vector_store: VectorStore) -> int:
    """采集并存储 Wiki 数据"""
    logger.info("=== 开始采集 Wiki 数据 ===")
    wiki_docs = fetch_wiki()

    all_chunks = []
    for doc in wiki_docs:
        chunks = chunk_wiki_article(doc, chunk_size=1000, overlap=200)
        all_chunks.extend(chunks)

    if all_chunks:
        vector_store.upsert_documents("wiki", all_chunks)

    logger.info(f"Wiki 数据采集完成: {len(wiki_docs)} 篇文章, {len(all_chunks)} 个文档块")
    return len(all_chunks)


def run_ingest(source: str = "all", incremental: bool = False):
    """
    执行数据采集

    Args:
        source: 数据源（heroes/items/abilities/patches/wiki/all）
        incremental: 是否增量更新模式
    """
    start_time = time.time()
    logger.info(f"开始数据采集任务: source={source}, incremental={incremental}")

    vector_store = VectorStore()
    tracker = VersionTracker()
    total_docs = 0

    # 增量模式：先检查哪些需要更新
    freshness = None
    if incremental:
        logger.info("增量模式: 检查数据新鲜度...")
        freshness = tracker.check_freshness()
        for name, detail in freshness.get("details", {}).items():
            logger.info(f"  {detail.get('message', name)}")
        if not freshness.get("needs_update"):
            logger.info("所有数据均为最新，无需更新")
            return

    # 获取版本追踪信息（用于增量补丁采集）
    meta = tracker.read_version_meta()

    source_handlers = {
        "heroes": lambda: _ingest_source_heroes(vector_store, tracker, freshness),
        "items": lambda: _ingest_source_items(vector_store, tracker, freshness),
        "abilities": lambda: _ingest_source_abilities(vector_store, tracker),
        "patches": lambda: _ingest_source_patches(vector_store, tracker, meta, freshness, incremental),
        "wiki": lambda: _ingest_source_wiki(vector_store, tracker),
    }

    if source == "all":
        for name, handler in source_handlers.items():
            # 增量模式：跳过不需要更新的数据源
            if incremental and freshness:
                detail = freshness.get("details", {}).get(name, {})
                if not detail.get("needs_update", True):
                    logger.info(f"跳过 {name}: 已是最新")
                    continue
            try:
                count = handler()
                total_docs += count
            except Exception as e:
                logger.error(f"采集 {name} 失败: {e}", exc_info=True)
    elif source in source_handlers:
        total_docs = source_handlers[source]()
    else:
        logger.error(f"未知的数据源: {source}")
        sys.exit(1)

    elapsed = time.time() - start_time
    logger.info(f"数据采集完成! 共 {total_docs} 个文档, 耗时 {elapsed:.1f} 秒")

    # 显示各 Collection 统计
    for collection in vector_store.list_collections():
        count = vector_store.get_collection_count(collection)
        logger.info(f"  {collection}: {count} 个文档")


def _ingest_source_heroes(vector_store, tracker, freshness):
    """采集英雄数据并更新版本追踪"""
    count = ingest_heroes(vector_store)
    tracker.update_source_meta("heroes", count)
    return count


def _ingest_source_items(vector_store, tracker, freshness):
    """采集物品数据并更新版本追踪"""
    count = ingest_items(vector_store)
    tracker.update_source_meta("items", count)
    return count


def _ingest_source_abilities(vector_store, tracker):
    """采集技能数据并更新版本追踪"""
    count = ingest_abilities(vector_store)
    tracker.update_source_meta("abilities", count)
    return count


def _ingest_source_patches(vector_store, tracker, meta, freshness, incremental=False):
    """采集补丁数据并更新版本追踪"""
    # 仅在增量模式下使用 since_version
    since_version = None
    if incremental:
        since_version = meta.get("sources", {}).get("patches", {}).get("latest_patch") or None
    count, latest_patch = ingest_patches(vector_store, since_version=since_version)

    # 使用采集返回的最新版本号，如果为空则从 freshness 中获取
    if not latest_patch and freshness:
        latest_patch = freshness.get("details", {}).get("patches", {}).get("remote_latest", "")

    tracker.update_source_meta("patches", count, latest_patch=latest_patch)
    return count


def _ingest_source_wiki(vector_store, tracker):
    """采集 Wiki 数据并更新版本追踪"""
    count = ingest_wiki(vector_store)
    tracker.update_source_meta("wiki", count)
    return count


def run_check():
    """
    检查数据是否需要更新（不执行采集）。

    输出各数据源的更新状态摘要。
    """
    logger.info("=== 数据新鲜度检查 ===")
    tracker = VersionTracker()

    meta = tracker.read_version_meta()
    logger.info(f"本地数据版本: {meta.get('game_version', '(未知)')}")
    logger.info(f"最后更新时间: {meta.get('last_updated', '(从未更新)')}")
    logger.info("")

    freshness = tracker.check_freshness()

    for name, detail in freshness.get("details", {}).items():
        msg = detail.get("message", f"{name}: 未知")
        status = "⚠️  需要更新" if detail.get("needs_update") else "✅ 已是最新"
        logger.info(f"  {status} | {msg}")

    logger.info("")
    if freshness.get("needs_update"):
        logger.info("建议执行: python -m src.ingestion.runner --all")
        logger.info("或增量更新: python -m src.ingestion.runner --incremental")
    else:
        logger.info("所有数据均为最新，无需更新。")


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(description="Dota 2 RAG 数据采集工具")
    parser.add_argument(
        "--all", action="store_true",
        help="全量采集所有数据源"
    )
    parser.add_argument(
        "--source", type=str, default=None,
        choices=["heroes", "items", "abilities", "patches", "wiki"],
        help="指定单个数据源采集"
    )
    parser.add_argument(
        "--incremental", action="store_true",
        help="增量更新模式：仅采集有变化的数据源"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="仅检查数据是否需要更新，不执行采集"
    )

    args = parser.parse_args()

    if args.check:
        run_check()
    elif args.incremental:
        run_ingest("all", incremental=True)
    elif args.all:
        run_ingest("all")
    elif args.source:
        run_ingest(args.source)
    else:
        # 默认全量采集
        run_ingest("all")


if __name__ == "__main__":
    main()
