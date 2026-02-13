"""GET /api/health、GET /api/stats 和 GET /api/data/status 路由"""
import logging

import httpx
from fastapi import APIRouter

from config.settings import settings
from src.api.schemas import (
    HealthResponse, StatsResponse, CollectionStats,
    DataStatusResponse, SourceStatusInfo,
)
from src.ingestion.version_tracker import VersionTracker
from src.vectorstore.store import VectorStore, COLLECTIONS

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_vector_store() -> VectorStore:
    """获取向量存储实例"""
    return VectorStore()


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health():
    """
    返回服务健康状态，包括 ChromaDB 连接和模型 API 可达性。
    """
    chroma_status = "disconnected"
    collections_count = {}
    model_api_status = "unreachable"
    
    # 检查 ChromaDB
    try:
        vs = _get_vector_store()
        for name in COLLECTIONS.values():
            collections_count[name] = vs.get_collection_count(name)
        chroma_status = "connected"
    except Exception as e:
        logger.warning(f"ChromaDB 健康检查失败: {e}")
    
    # 检查模型 API
    try:
        url = f"{settings.API_BASE_URL}/models"
        headers = {"Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10.0)
            if resp.status_code in (200, 401, 403):
                # 401/403 说明 API 端点可达，只是认证问题
                model_api_status = "reachable"
    except Exception as e:
        logger.warning(f"模型 API 健康检查失败: {e}")
    
    # 判断总体状态
    if chroma_status == "connected" and model_api_status == "reachable":
        status = "healthy"
    elif chroma_status == "connected":
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        chroma=chroma_status,
        collections=collections_count,
        model_api=model_api_status,
    )


@router.get("/stats", response_model=StatsResponse, summary="数据统计")
async def stats():
    """
    返回各 Collection 的文档统计信息。
    """
    collection_stats = []
    total = 0
    
    try:
        vs = _get_vector_store()
        for name in COLLECTIONS.values():
            count = vs.get_collection_count(name)
            total += count
            collection_stats.append(CollectionStats(
                name=name,
                document_count=count,
            ))
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
    
    return StatsResponse(
        collections=collection_stats,
        total_documents=total,
    )


@router.get("/data/status", response_model=DataStatusResponse, summary="数据版本状态")
async def data_status():
    """
    返回当前向量库中各数据源的版本、更新时间、文档数量等状态信息。

    读取 data/version_meta.json 文件并返回。
    """
    tracker = VersionTracker()
    meta = tracker.read_version_meta()

    sources = {}
    for source_name, source_info in meta.get("sources", {}).items():
        sources[source_name] = SourceStatusInfo(
            count=source_info.get("count", 0),
            updated_at=source_info.get("updated_at"),
            latest_patch=source_info.get("latest_patch"),
        )

    return DataStatusResponse(
        last_updated=meta.get("last_updated"),
        game_version=meta.get("game_version"),
        sources=sources,
    )
