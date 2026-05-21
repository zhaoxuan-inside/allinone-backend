from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ToolBase(BaseModel):
    """工具基础信息"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str
    icon: Optional[str] = None
    category: str
    is_frontend: bool = True
    is_backend: bool = False
    endpoint: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    response_format: Optional[Dict[str, Any]] = None


class ToolCreate(ToolBase):
    """创建工具"""
    pass


class ToolUpdate(BaseModel):
    """更新工具"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    is_frontend: Optional[bool] = None
    is_backend: Optional[bool] = None
    endpoint: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    response_format: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class Tool(ToolBase):
    """工具完整信息"""
    id: UUID
    enabled: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ToolSummary(BaseModel):
    """工具摘要信息"""
    id: UUID
    name: str
    description: str
    icon: Optional[str]
    category: str
    is_frontend: bool
    is_backend: bool

    class Config:
        from_attributes = True


class ToolCategory(BaseModel):
    """工具分类"""
    name: str
    display_name: str
    icon: Optional[str] = None
    description: Optional[str] = None
    tool_count: int = 0


class ToolListResponse(BaseModel):
    """工具列表响应"""
    tools: List[ToolSummary]
    total: int


class ToolDetailResponse(BaseModel):
    """工具详情响应"""
    tool: Tool
    related_tools: List[ToolSummary] = []


class ToolExecutionRequest(BaseModel):
    """工具执行请求"""
    parameters: Dict[str, Any]


class ToolExecutionResponse(BaseModel):
    """工具执行响应"""
    success: bool
    result: Optional[Any] = None
    message: Optional[str] = None
    execution_time_ms: Optional[int] = None