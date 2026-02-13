"""FastAPI 应用入口"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Dota 2 RAG 服务启动中...")
    logger.info(f"API Base URL: {settings.API_BASE_URL}")
    logger.info(f"Embedding 模型: {settings.EMBEDDING_MODEL}")
    logger.info(f"Chat 模型: {settings.CHAT_MODEL}")
    yield
    logger.info("Dota 2 RAG 服务关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Dota 2 RAG 知识问答服务",
    description="基于 RAG 的 Dota 2 智能问答 API，支持英雄、物品、版本更新等知识查询",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求的元数据和耗时"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"-> {response.status_code} ({duration_ms:.1f}ms)"
    )
    
    return response


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，返回统一 JSON 错误格式"""
    logger.error(f"未预期的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "服务器内部错误，请稍后重试",
        },
    )


@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc):
    """限流响应处理"""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limited",
            "message": "请求过于频繁，请稍后重试",
        },
        headers={"Retry-After": "30"},
    )


# 注册路由
from src.api.routes.ask import router as ask_router
from src.api.routes.ingest import router as ingest_router
from src.api.routes.health import router as health_router

app.include_router(ask_router, prefix="/api", tags=["问答"])
app.include_router(ingest_router, prefix="/api", tags=["数据采集"])
app.include_router(health_router, prefix="/api", tags=["运维"])


# 根路由
@app.get("/", summary="服务信息")
async def root():
    return {
        "service": "Dota 2 RAG 知识问答服务",
        "version": "1.0.0",
        "docs": "/docs",
        "api": {
            "ask": "POST /api/ask",
            "ingest": "POST /api/ingest",
            "health": "GET /api/health",
            "stats": "GET /api/stats",
        },
    }
