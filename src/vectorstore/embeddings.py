"""Embedding 向量化封装"""
import logging
from typing import List

from langchain_openai import OpenAIEmbeddings

from config.settings import settings

logger = logging.getLogger(__name__)


class DashScopeEmbeddings(OpenAIEmbeddings):
    """阿里云 DashScope Embedding 封装（兼容 OpenAI 格式）"""
    
    def __init__(self):
        """初始化 DashScope Embedding 客户端"""
        super().__init__(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.DASHSCOPE_API_KEY,
            openai_api_base=settings.API_BASE_URL,
            chunk_size=6,  # DashScope 每批最多 10 个，留余量设为 6
            # 关键：禁用 tiktoken 分词，直接发送原始字符串
            # DashScope 不支持 token 数组格式，只接受字符串输入
            check_embedding_ctx_length=False,
        )
        logger.info(
            f"初始化 Embedding 客户端: model={settings.EMBEDDING_MODEL}, "
            f"base_url={settings.API_BASE_URL}"
        )


def get_embeddings() -> DashScopeEmbeddings:
    """
    获取 Embedding 实例
    
    Returns:
        DashScopeEmbeddings 实例
    """
    return DashScopeEmbeddings()
