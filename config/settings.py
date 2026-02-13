"""配置管理模块，从环境变量读取配置"""
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""
    
    # API Key（必需）- 支持阿里云 DashScope / 硅基流动等 OpenAI 兼容平台
    DASHSCOPE_API_KEY: str = ""
    
    # API 平台配置
    API_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v3"
    CHAT_MODEL: str = "qwen-plus"
    
    # ChromaDB 配置
    CHROMA_PERSIST_DIR: str = "data/chroma_db"
    
    # API 服务配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # 缓存配置
    CACHE_TTL: int = 3600  # 默认 1 小时
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    def __init__(self, **kwargs):
        """初始化配置，检查必需的环境变量"""
        super().__init__(**kwargs)
        self._validate_required()
    
    def _validate_required(self) -> None:
        """验证必需配置是否存在"""
        if not self.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
    
    @property
    def chroma_persist_path(self) -> Path:
        """返回 ChromaDB 持久化路径（Path 对象）"""
        return Path(self.CHROMA_PERSIST_DIR)


# 全局配置实例
settings = Settings()
