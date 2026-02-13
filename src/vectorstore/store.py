"""ChromaDB 向量存储封装"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config.settings import settings
from .embeddings import get_embeddings

logger = logging.getLogger(__name__)

# Collection 名称
COLLECTIONS = {
    "heroes": "heroes",
    "items": "items",
    "patches": "patches",
    "wiki": "wiki",
}


class VectorStore:
    """ChromaDB 向量存储管理器"""
    
    def __init__(self):
        """初始化向量存储"""
        self.persist_dir = settings.chroma_persist_path
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        
        # 初始化 Embedding 函数
        self.embeddings = get_embeddings()
        
        # 为每个 Collection 创建 LangChain Chroma 实例
        self.stores: Dict[str, Chroma] = {}
        for collection_name in COLLECTIONS.values():
            self.stores[collection_name] = Chroma(
                client=self.client,
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_dir),
            )
        
        logger.info(f"初始化 ChromaDB 向量存储，持久化目录: {self.persist_dir}")
    
    def upsert_documents(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
    ) -> None:
        """
        插入或更新文档
        
        Args:
            collection: Collection 名称（heroes/items/patches/wiki）
            documents: 文档列表，每个文档包含 content 和 metadata
        """
        if collection not in COLLECTIONS.values():
            raise ValueError(f"无效的 Collection 名称: {collection}")
        
        store = self.stores[collection]
        
        # 转换为 LangChain Document 格式
        langchain_docs = []
        ids = []
        for i, doc in enumerate(documents):
            # 使用 entity_name + chunk_index 作为唯一 ID
            entity_name = doc.get("metadata", {}).get("entity_name", "")
            chunk_index = doc.get("metadata", {}).get("chunk_index", 0)
            doc_id = f"{entity_name}_{chunk_index}_{i}" if entity_name else f"doc_{i}"
            
            langchain_doc = Document(
                page_content=doc.get("content", ""),
                metadata=doc.get("metadata", {}),
            )
            langchain_docs.append(langchain_doc)
            ids.append(doc_id)
        
        # 分批添加文档（DashScope Embedding API 每批最多 10 个）
        batch_size = 6
        total_added = 0
        for i in range(0, len(langchain_docs), batch_size):
            batch_docs = langchain_docs[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            store.add_documents(batch_docs, ids=batch_ids)
            total_added += len(batch_docs)
            if total_added % 30 == 0 or total_added == len(langchain_docs):
                logger.info(f"  已添加 {total_added}/{len(langchain_docs)} 个文档到 {collection}")
        
        logger.info(f"向 {collection} Collection 添加了 {len(documents)} 个文档")
    
    def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        相似度搜索
        
        Args:
            collection: Collection 名称
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 元数据过滤条件
            
        Returns:
            相关文档列表
        """
        if collection not in COLLECTIONS.values():
            raise ValueError(f"无效的 Collection 名称: {collection}")
        
        store = self.stores[collection]
        
        logger.info(f"[VectorStore] 搜索 collection='{collection}', query='{query[:80]}', top_k={top_k}, filter={filter_dict}")
        
        # 执行搜索
        results = store.similarity_search(
            query,
            k=top_k,
            filter=filter_dict,
        )
        
        logger.info(f"[VectorStore] collection='{collection}' 搜索返回 {len(results)} 条结果")
        for i, doc in enumerate(results):
            logger.info(
                f"[VectorStore] 结果[{i}] entity={doc.metadata.get('entity_name','?')}, "
                f"内容前80字: {doc.page_content[:80]!r}"
            )
        
        return results
    
    def get_collection_count(self, collection: str) -> int:
        """
        获取 Collection 中的文档数量
        
        Args:
            collection: Collection 名称
            
        Returns:
            文档数量
        """
        if collection not in COLLECTIONS.values():
            raise ValueError(f"无效的 Collection 名称: {collection}")
        
        store = self.stores[collection]
        return store._collection.count()
    
    def clear_collection(self, collection: str) -> None:
        """
        清空 Collection
        
        Args:
            collection: Collection 名称
        """
        if collection not in COLLECTIONS.values():
            raise ValueError(f"无效的 Collection 名称: {collection}")
        
        # 删除并重建 Collection
        self.client.delete_collection(name=collection)
        self.stores[collection] = Chroma(
            client=self.client,
            collection_name=collection,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_dir),
        )
        logger.info(f"已清空 {collection} Collection")
    
    def list_collections(self) -> List[str]:
        """
        列出所有 Collection
        
        Returns:
            Collection 名称列表
        """
        return list(COLLECTIONS.values())
