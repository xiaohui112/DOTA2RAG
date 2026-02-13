"""POST /api/ingest 数据采集路由"""
import logging
import asyncio

from fastapi import APIRouter, BackgroundTasks

from src.api.schemas import IngestRequest, IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_ingest(source: str):
    """后台执行数据采集任务"""
    try:
        from src.ingestion.sources.heroes import fetch_heroes
        from src.ingestion.sources.items import fetch_items
        from src.ingestion.processors.cleaner import add_metadata
        from src.ingestion.processors.chunker import chunk_hero_item
        from src.vectorstore.store import VectorStore
        
        vector_store = VectorStore()
        
        if source in ("heroes", "all"):
            logger.info("开始采集英雄数据...")
            heroes = fetch_heroes()
            hero_chunks = []
            for hero in heroes:
                hero_with_meta = add_metadata(
                    hero, "api", "hero",
                    hero.get("localized_name", hero.get("name", ""))
                )
                hero_chunks.extend(chunk_hero_item(hero_with_meta, "hero"))
            vector_store.upsert_documents("heroes", hero_chunks)
            logger.info(f"英雄数据采集完成: {len(hero_chunks)} 个文档")
        
        if source in ("items", "all"):
            logger.info("开始采集物品数据...")
            items = fetch_items()
            item_chunks = []
            for item in items:
                # 兼容官方 API 和 OpenDota API 的数据格式
                item_name = (
                    item.get("name_loc") or  # 官方 API 中文名
                    item.get("dname") or  # OpenDota API 显示名
                    item.get("name_english_loc") or  # 官方 API 英文名
                    item.get("name", "")
                )
                item_with_meta = add_metadata(
                    item, "api", "item",
                    item_name
                )
                item_chunks.extend(chunk_hero_item(item_with_meta, "item"))
            vector_store.upsert_documents("items", item_chunks)
            logger.info(f"物品数据采集完成: {len(item_chunks)} 个文档")
        
        if source in ("patches", "all"):
            logger.info("Patches 数据采集（暂未实现）")
        
        if source in ("wiki", "all"):
            logger.info("Wiki 数据采集（暂未实现）")
        
        logger.info(f"数据采集任务完成: source={source}")
        
    except Exception as e:
        logger.error(f"数据采集失败: {e}", exc_info=True)


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=202,
    summary="触发数据采集",
)
async def ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    """
    触发数据采集任务（异步后台执行）。
    
    支持的数据源：heroes、items、patches、wiki、all
    """
    background_tasks.add_task(_run_ingest, request.source)
    
    return IngestResponse(
        status="accepted",
        message=f"数据采集任务已触发: {request.source}",
        source=request.source,
    )
