"""API 请求/响应 Pydantic 模型"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    top_k: int = Field(default=5, ge=1, le=20, description="检索返回文档数")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM 温度参数")
    max_tokens: int = Field(default=2048, ge=100, le=8192, description="LLM 最大生成 token 数")
    enable_translation: bool = Field(default=True, description="是否启用中文查询翻译")
    
    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("问题不能为空")
        if len(v) > 1000:
            raise ValueError("问题长度不能超过 1000 个字符")
        return v


class SourceInfo(BaseModel):
    """来源信息"""
    collection: str = Field(description="来源 Collection")
    entity_name: str = Field(description="实体名称")
    source: str = Field(description="数据来源类型")
    category: str = Field(description="数据类别")


class AskResponse(BaseModel):
    """问答响应"""
    answer: str = Field(description="生成的回答")
    sources: List[SourceInfo] = Field(default_factory=list, description="来源归因")
    cached: bool = Field(default=False, description="是否来自缓存")


class IngestRequest(BaseModel):
    """数据采集请求"""
    source: str = Field(default="all", description="数据源名称")
    
    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        valid_sources = {"heroes", "items", "patches", "wiki", "all"}
        if v not in valid_sources:
            raise ValueError(f"无效的数据源 '{v}'，有效选项: {', '.join(sorted(valid_sources))}")
        return v


class IngestResponse(BaseModel):
    """数据采集响应"""
    status: str = Field(description="任务状态")
    message: str = Field(description="状态信息")
    source: str = Field(description="触发的数据源")


class CollectionStats(BaseModel):
    """Collection 统计信息"""
    name: str
    document_count: int
    last_updated: Optional[str] = None


class StatsResponse(BaseModel):
    """统计响应"""
    collections: List[CollectionStats]
    total_documents: int


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="healthy / degraded / unhealthy")
    chroma: str = Field(description="ChromaDB 连接状态")
    collections: Dict[str, int] = Field(description="各 Collection 文档数")
    model_api: str = Field(description="模型 API 可达性")


class SourceStatusInfo(BaseModel):
    """单个数据源的版本状态信息"""
    count: int = Field(default=0, description="文档数量")
    updated_at: Optional[str] = Field(default=None, description="最后更新时间")
    latest_patch: Optional[str] = Field(default=None, description="最新补丁版本号（仅 patches）")


class DataStatusResponse(BaseModel):
    """数据版本状态响应"""
    last_updated: Optional[str] = Field(default=None, description="全局最后更新时间")
    game_version: Optional[str] = Field(default=None, description="当前游戏版本号")
    sources: Dict[str, SourceStatusInfo] = Field(default_factory=dict, description="各数据源状态")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(description="错误类型")
    message: str = Field(description="可读错误信息")
