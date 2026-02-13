"""POST /api/ask 问答路由"""
import logging

from fastapi import APIRouter, HTTPException

from src.api.schemas import AskRequest, AskResponse, SourceInfo
from src.rag.chain import RAGChain

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局 RAG Chain 实例（延迟初始化）
_rag_chain: RAGChain = None


def get_rag_chain() -> RAGChain:
    """获取或初始化 RAG Chain"""
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = RAGChain()
    return _rag_chain


@router.post("/ask", response_model=AskResponse, summary="Dota 2 知识问答")
async def ask(request: AskRequest):
    """
    提交 Dota 2 相关问题，获取基于知识库的回答。
    
    支持中英文查询，可选配置检索参数。
    """
    try:
        chain = get_rag_chain()
        
        result = await chain.ask(
            question=request.question,
            top_k=request.top_k,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            enable_translation=request.enable_translation,
        )
        
        # 构建来源信息
        sources = [
            SourceInfo(**s) for s in result.get("sources", [])
        ]
        
        return AskResponse(
            answer=result["answer"],
            sources=sources,
            cached=result.get("cached", False),
        )
        
    except Exception as e:
        logger.error(f"问答处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "服务器内部错误，请稍后重试"}
        )
