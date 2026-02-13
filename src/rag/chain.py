"""RAG Chain 核心逻辑：组装上下文、调用 LLM、缓存、来源归因"""
import hashlib
import logging
import time
from typing import Dict, Any, Optional, List

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

from config.settings import settings
from src.vectorstore.store import VectorStore
from src.rag.prompts import SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE
from src.rag.retriever import retrieve

logger = logging.getLogger(__name__)


class ResponseCache:
    """简单的内存缓存，基于查询文本的 hash"""
    
    def __init__(self, ttl: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl
    
    def _make_key(self, query: str, top_k: int, temperature: float) -> str:
        """生成缓存键"""
        raw = f"{query.strip().lower()}|{top_k}|{temperature}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    def get(self, query: str, top_k: int = 5, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """查询缓存"""
        key = self._make_key(query, top_k, temperature)
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() - entry["timestamp"] > self._ttl:
            del self._cache[key]
            return None
        return entry["data"]
    
    def set(self, query: str, data: Dict[str, Any], top_k: int = 5, temperature: float = 0.3):
        """写入缓存"""
        key = self._make_key(query, top_k, temperature)
        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
        }
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()


class RAGChain:
    """RAG 问答链"""
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        初始化 RAG Chain
        
        Args:
            vector_store: 向量存储实例，如果为 None 则自动创建
        """
        self.vector_store = vector_store or VectorStore()
        self.cache = ResponseCache(ttl=settings.CACHE_TTL)
        logger.info("RAG Chain 初始化完成")
    
    def _build_context(self, documents: List[Document]) -> str:
        """
        将检索到的文档组装为上下文字符串
        
        Args:
            documents: 文档列表
            
        Returns:
            格式化的上下文字符串
        """
        if not documents:
            return "（未找到相关文档）"
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "unknown")
            category = doc.metadata.get("category", "unknown")
            entity = doc.metadata.get("entity_name", "unknown")
            
            context_parts.append(
                f"### 文档 {i} [{category}/{entity}]\n{doc.page_content}"
            )
        
        return "\n\n".join(context_parts)
    
    def _get_llm(self, temperature: float = 0.3, max_tokens: int = 2048) -> ChatOpenAI:
        """获取 LLM 实例"""
        return ChatOpenAI(
            model=settings.CHAT_MODEL,
            openai_api_key=settings.DASHSCOPE_API_KEY,
            openai_api_base=settings.API_BASE_URL,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    async def ask(
        self,
        question: str,
        top_k: int = 5,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        enable_translation: bool = True,
    ) -> Dict[str, Any]:
        """
        RAG 问答主流程
        
        Args:
            question: 用户问题
            top_k: 检索返回的文档数
            temperature: LLM 温度参数
            max_tokens: LLM 最大 token 数
            enable_translation: 是否启用查询翻译
            
        Returns:
            {"answer": str, "sources": list, "cached": bool}
        """
        # 1. 检查缓存
        cached = self.cache.get(question, top_k, temperature)
        if cached is not None:
            logger.info(f"缓存命中: '{question[:30]}...'")
            cached["cached"] = True
            return cached
        
        # 2. 检索相关文档
        documents, sources = await retrieve(
            vector_store=self.vector_store,
            query=question,
            top_k=top_k,
            enable_translation=enable_translation,
        )
        logger.info(f"[RAG] 检索到 {len(documents)} 个文档, sources 数量: {len(sources)}")
        for i, doc in enumerate(documents):
            logger.info(
                f"[RAG] 文档[{i}] source={doc.metadata.get('source','?')}, "
                f"entity={doc.metadata.get('entity_name','?')}, "
                f"内容前100字: {doc.page_content[:100]!r}"
            )
        
        # 3. 组装上下文
        context = self._build_context(documents)
        logger.info(f"[RAG] 组装后 context 长度: {len(context)} 字符")
        logger.debug(f"[RAG] context 全文:\n{context}")
        
        # 4. 构建 Prompt
        user_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        logger.info(f"[RAG] 最终 user_prompt 长度: {len(user_prompt)} 字符")
        logger.info(f"[RAG] user_prompt 前500字:\n{user_prompt[:500]}")
        
        # 5. 调用 LLM（带重试）
        llm = self._get_llm(temperature=temperature, max_tokens=max_tokens)
        
        last_error = None
        for attempt in range(3):
            try:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
                logger.info(f"[RAG] 发送给 LLM 的 messages 数量: {len(messages)}, system_prompt 长度: {len(SYSTEM_PROMPT)}, user_prompt 长度: {len(user_prompt)}")
                response = await llm.ainvoke(messages)
                answer = response.content
                logger.info(f"[RAG] LLM 返回 answer 长度: {len(answer)} 字符, 前200字: {answer[:200]!r}")
                
                # 6. 构建响应
                result = {
                    "answer": answer,
                    "sources": sources,
                    "cached": False,
                }
                
                # 7. 写入缓存
                self.cache.set(question, result, top_k, temperature)
                
                logger.info(f"回答生成成功: '{question[:30]}...'")
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"LLM 调用失败 (第 {attempt + 1} 次): {e}")
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(1 * (attempt + 1))
        
        # 全部重试失败
        logger.error(f"LLM 调用全部失败: {last_error}")
        return {
            "answer": "服务暂时不可用，请稍后重试",
            "sources": sources,
            "cached": False,
            "error": str(last_error),
        }
