from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db
from common.permissions import Roles, require_role
from ai_service.schemas import (
    AIProvider, AIProviderCreate, AIProviderUpdate,
    Conversation, ConversationCreate, ConversationUpdate,
    MessageNode, MessageNodeSchema,
    ChatRequest, ChatResponse, StreamChatResponse,
    MessageHistoryResponse,
    ProviderListResponse, ConversationListResponse,
    PinRequest, TagRequest, SummarizeRequest
)
from ai_service.service import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


def get_ai_service(db: AsyncSession = Depends(get_db)) -> AIService:
    return AIService(db)


@router.get("/providers", response_model=ProviderListResponse)
async def get_providers(
    ai_service: AIService = Depends(get_ai_service)
):
    """获取AI提供商列表"""
    return await ai_service.get_providers()


@router.post("/providers", response_model=AIProvider)
async def create_provider(
    provider_data: AIProviderCreate,
    _=Depends(require_role(Roles.ADMIN)),
    ai_service: AIService = Depends(get_ai_service)
):
    """创建AI提供商（管理员）"""
    return await ai_service.create_provider(provider_data)


@router.put("/providers/{provider_id}", response_model=AIProvider)
async def update_provider(
    provider_id: UUID,
    provider_data: AIProviderUpdate,
    _=Depends(require_role(Roles.ADMIN)),
    ai_service: AIService = Depends(get_ai_service)
):
    """更新AI提供商（管理员）"""
    provider = await ai_service.update_provider(provider_id, provider_data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: UUID,
    _=Depends(require_role(Roles.ADMIN)),
    ai_service: AIService = Depends(get_ai_service)
):
    """删除AI提供商（管理员）"""
    success = await ai_service.delete_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"success": True}


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    ai_service: AIService = Depends(get_ai_service)
):
    """获取对话列表"""
    return await ai_service.get_conversations()


@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    conversation_data: ConversationCreate,
    ai_service: AIService = Depends(get_ai_service)
):
    """创建对话"""
    return await ai_service.create_conversation(conversation_data)


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: UUID,
    ai_service: AIService = Depends(get_ai_service)
):
    """获取对话"""
    conversation = await ai_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.put("/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: UUID,
    conversation_data: ConversationUpdate,
    ai_service: AIService = Depends(get_ai_service)
):
    """更新对话"""
    conversation = await ai_service.update_conversation(conversation_id, conversation_data)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    ai_service: AIService = Depends(get_ai_service)
):
    """删除对话"""
    success = await ai_service.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True}


@router.get("/conversations/{conversation_id}/messages", response_model=MessageHistoryResponse)
async def get_messages(
    conversation_id: UUID,
    max_messages: int = Query(20, ge=1, le=100),
    ai_service: AIService = Depends(get_ai_service)
):
    """获取消息历史"""
    return await ai_service.get_messages(conversation_id, max_messages)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """非流式聊天"""
    try:
        return await ai_service.chat(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """流式聊天"""
    try:
        return ai_service.stream_chat(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/messages/{node_id}/pin", response_model=MessageNodeSchema)
async def pin_message(
    node_id: UUID,
    pin_request: PinRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """置顶/取消置顶消息"""
    message = await ai_service.pin_message(pin_request.conversation_id, node_id, pin_request.pinned)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.post("/messages/{node_id}/tags", response_model=MessageNodeSchema)
async def add_tags(
    node_id: UUID,
    tag_request: TagRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """添加标签"""
    message = await ai_service.add_tags(tag_request.conversation_id, node_id, tag_request.tags)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.post("/messages/{node_id}/summarize", response_model=MessageNodeSchema)
async def summarize_message(
    node_id: UUID,
    summarize_request: SummarizeRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """总结消息"""
    message = await ai_service.summarize_message(summarize_request.conversation_id, node_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message