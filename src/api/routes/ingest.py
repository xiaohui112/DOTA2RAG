"""POST /api/ingest 数据采集路由"""
import asyncio
import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.api.schemas import IngestRequest, IngestResponse, IngestTaskStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# 任务状态注册表（进程内，重启后清空）
_tasks: Dict[str, dict] = {}


def _make_task(task_id: str, source: str) -> dict:
    return {
        "task_id": task_id,
        "source": source,
        "status": "pending",
        "started_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "completed_at": None,
        "error": None,
    }


async def _run_ingest(task_id: str, source: str):
    """后台执行数据采集任务（调用 runner.run_ingest）"""
    _tasks[task_id]["status"] = "running"
    try:
        from src.ingestion.runner import run_ingest

        loop = asyncio.get_event_loop()
        # run_ingest 是同步函数，放到线程池执行，避免阻塞事件循环
        await loop.run_in_executor(None, run_ingest, source)

        _tasks[task_id]["status"] = "completed"
        _tasks[task_id]["completed_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        logger.info(f"数据采集任务完成: task_id={task_id}, source={source}")

    except Exception as e:
        _tasks[task_id]["status"] = "failed"
        _tasks[task_id]["completed_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        _tasks[task_id]["error"] = str(e)
        logger.error(f"数据采集任务失败: task_id={task_id}, source={source}, error={e}", exc_info=True)


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
    返回 task_id，可通过 GET /api/ingest/{task_id} 查询进度。
    """
    task_id = str(uuid.uuid4())
    _tasks[task_id] = _make_task(task_id, request.source)
    background_tasks.add_task(_run_ingest, task_id, request.source)

    return IngestResponse(
        status="accepted",
        message=f"数据采集任务已触发: {request.source}，task_id={task_id}",
        source=request.source,
    )


@router.get(
    "/ingest/{task_id}",
    response_model=IngestTaskStatus,
    summary="查询数据采集任务状态",
)
async def get_ingest_status(task_id: str):
    """查询指定任务的执行状态"""
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return IngestTaskStatus(**task)
