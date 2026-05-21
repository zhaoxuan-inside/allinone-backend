from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AIProviderBase(BaseModel):
    """AI提供商基础信息"""
    name: str = Field(..., min_length=1, max_length=100)
    provider_type: str = Field(..., pattern="^(openai|anthropic|azure|ollama|local)$")
    api_endpoint: str
    api_key: Optional[str] = None
    model_name: str
    max_tokens: int = 4096
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    enabled: bool = True


class AIProviderCreate(AIProviderBase):
    """创建AI提供商"""
    pass


class AIProviderUpdate(BaseModel):
    """更新AI提供商"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider_type: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    enabled: Optional[bool] = None


class AIProvider(AIProviderBase):
    """AI提供商"""
    id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageNodeBase(BaseModel):
    """消息节点基础信息"""
    content: str
    role: str = Field(..., pattern="^(user|assistant|system)$")
    parent_id: Optional[UUID] = None
    root_id: Optional[UUID] = None
    pinned: bool = False
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


class MessageNodeCreate(MessageNodeBase):
    """创建消息节点"""
    conversation_id: UUID


class MessageNode(MessageNodeBase):
    """消息节点"""
    id: UUID
    conversation_id: UUID
    created_at: datetime
    updated_at: datetime
    is_summarized: bool = False
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class MessageNodeWithChildren(MessageNode):
    """消息节点及其子节点"""
    children: List["MessageNodeWithChildren"] = []


class ConversationBase(BaseModel):
    """对话基础信息"""
    title: Optional[str] = None
    provider_id: UUID
    system_prompt: Optional[str] = None


class ConversationCreate(ConversationBase):
    """创建对话"""
    pass


class ConversationUpdate(BaseModel):
    """更新对话"""
    title: Optional[str] = None
    system_prompt: Optional[str] = None


class Conversation(ConversationBase):
    """对话"""
    id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationWithMessages(Conversation):
    """带消息的对话"""
    messages: List[MessageNode] = []


class ChatRequest(BaseModel):
    """聊天请求"""
    conversation_id: Optional[UUID] = None
    provider_id: UUID
    message: str
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    stream: bool = True


class ChatResponse(BaseModel):
    """聊天响应"""
    conversation_id: UUID
    message_id: UUID
    content: str
    finish_reason: str = "stop"


class StreamChatResponse(BaseModel):
    """流式聊天响应"""
    conversation_id: UUID
    message_id: UUID
    delta: str
    done: bool = False


class MessageHistoryRequest(BaseModel):
    """消息历史请求"""
    conversation_id: UUID
    node_id: Optional[UUID] = None
    max_messages: int = Field(20, ge=1, le=100)
    include_pinned: bool = True


class MessageHistoryResponse(BaseModel):
    """消息历史响应"""
    conversation_id: UUID
    messages: List[MessageNode]
    total_count: int


class TagRequest(BaseModel):
    """标签请求"""
    conversation_id: UUID
    node_id: UUID
    tags: List[str]


class PinRequest(BaseModel):
    """置顶请求"""
    conversation_id: UUID
    node_id: UUID
    pinned: bool


class SummarizeRequest(BaseModel):
    """总结请求"""
    conversation_id: UUID
    node_id: UUID


class ProviderListResponse(BaseModel):
    """提供商列表响应"""
    providers: List[AIProvider]
    total: int


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    conversations: List[Conversation]
    total: int