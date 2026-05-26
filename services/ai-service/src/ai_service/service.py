from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime
import httpx
import json

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai_service.entities import AIProvider, Conversation, MessageNode
from src.ai_service.repository import AIProviderRepository, ConversationRepository, MessageNodeRepository
from src.ai_service.schemas import (
    AIProvider as AIProviderSchema,
    AIProviderCreate, AIProviderUpdate,
    Conversation as ConversationSchema,
    ConversationCreate, ConversationUpdate,
    MessageNode as MessageNodeSchema,
    MessageNodeCreate,
    ChatRequest, ChatResponse, StreamChatResponse,
    MessageHistoryResponse,
    ProviderListResponse, ConversationListResponse
)


class AIService:
    def __init__(self, db_session: AsyncSession):
        self.provider_repo = AIProviderRepository(db_session)
        self.conversation_repo = ConversationRepository(db_session)
        self.message_repo = MessageNodeRepository(db_session)

    async def get_providers(self, user_id: Optional[UUID] = None) -> ProviderListResponse:
        """获取AI提供商列表"""
        providers = await self.provider_repo.get_all_providers(user_id)
        provider_schemas = [
            AIProviderSchema(
                id=p.id,
                user_id=p.user_id,
                name=p.name,
                provider_type=p.provider_type,
                api_endpoint=p.api_endpoint,
                api_key=p.api_key,
                model_name=p.model_name,
                max_tokens=p.max_tokens,
                temperature=p.temperature,
                enabled=p.enabled,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in providers
        ]
        return ProviderListResponse(providers=provider_schemas, total=len(provider_schemas))

    async def create_provider(self, provider_data: AIProviderCreate, user_id: Optional[UUID] = None) -> AIProviderSchema:
        """创建AI提供商"""
        data = provider_data.model_dump()
        data["user_id"] = user_id
        provider = await self.provider_repo.create_provider(data)
        return AIProviderSchema(
            id=provider.id,
            user_id=provider.user_id,
            name=provider.name,
            provider_type=provider.provider_type,
            api_endpoint=provider.api_endpoint,
            api_key=provider.api_key,
            model_name=provider.model_name,
            max_tokens=provider.max_tokens,
            temperature=provider.temperature,
            enabled=provider.enabled,
            created_at=provider.created_at,
            updated_at=provider.updated_at
        )

    async def update_provider(self, provider_id: UUID, provider_data: AIProviderUpdate) -> Optional[AIProviderSchema]:
        """更新AI提供商"""
        update_data = {k: v for k, v in provider_data.model_dump().items() if v is not None}
        provider = await self.provider_repo.update_provider(provider_id, update_data)
        if not provider:
            return None
        return AIProviderSchema(
            id=provider.id,
            user_id=provider.user_id,
            name=provider.name,
            provider_type=provider.provider_type,
            api_endpoint=provider.api_endpoint,
            api_key=provider.api_key,
            model_name=provider.model_name,
            max_tokens=provider.max_tokens,
            temperature=provider.temperature,
            enabled=provider.enabled,
            created_at=provider.created_at,
            updated_at=provider.updated_at
        )

    async def delete_provider(self, provider_id: UUID) -> bool:
        """删除AI提供商"""
        return await self.provider_repo.delete_provider(provider_id)

    async def get_conversations(self, user_id: Optional[UUID] = None) -> ConversationListResponse:
        """获取对话列表"""
        conversations = await self.conversation_repo.get_all_conversations(user_id)
        conversation_schemas = [
            ConversationSchema(
                id=c.id,
                user_id=c.user_id,
                provider_id=c.provider_id,
                title=c.title,
                system_prompt=c.system_prompt,
                created_at=c.created_at,
                updated_at=c.updated_at,
                last_message_at=c.last_message_at
            )
            for c in conversations
        ]
        return ConversationListResponse(conversations=conversation_schemas, total=len(conversation_schemas))

    async def create_conversation(self, conversation_data: ConversationCreate, user_id: Optional[UUID] = None) -> ConversationSchema:
        """创建对话"""
        data = conversation_data.model_dump()
        data["user_id"] = user_id
        conversation = await self.conversation_repo.create_conversation(data)
        return ConversationSchema(
            id=conversation.id,
            user_id=conversation.user_id,
            provider_id=conversation.provider_id,
            title=conversation.title,
            system_prompt=conversation.system_prompt,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at
        )

    async def get_conversation(self, conversation_id: UUID) -> Optional[ConversationSchema]:
        """获取对话"""
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        if not conversation:
            return None
        return ConversationSchema(
            id=conversation.id,
            user_id=conversation.user_id,
            provider_id=conversation.provider_id,
            title=conversation.title,
            system_prompt=conversation.system_prompt,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at
        )

    async def update_conversation(self, conversation_id: UUID, conversation_data: ConversationUpdate) -> Optional[ConversationSchema]:
        """更新对话"""
        update_data = {k: v for k, v in conversation_data.model_dump().items() if v is not None}
        conversation = await self.conversation_repo.update_conversation(conversation_id, update_data)
        if not conversation:
            return None
        return ConversationSchema(
            id=conversation.id,
            user_id=conversation.user_id,
            provider_id=conversation.provider_id,
            title=conversation.title,
            system_prompt=conversation.system_prompt,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at
        )

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        """删除对话"""
        return await self.conversation_repo.delete_conversation(conversation_id)

    async def get_messages(self, conversation_id: UUID, max_messages: int = 20) -> MessageHistoryResponse:
        """获取消息历史"""
        messages = await self.message_repo.get_messages_by_conversation(conversation_id, max_messages)
        message_schemas = [
            MessageNodeSchema(
                id=m.id,
                conversation_id=m.conversation_id,
                content=m.content if not m.is_summarized else (m.summary or m.content),
                role=m.role,
                parent_id=m.parent_id,
                root_id=m.root_id,
                pinned=m.pinned,
                tags=list(m.tags) if m.tags else [],
                metadata=m.metadata,
                is_summarized=m.is_summarized,
                summary=m.summary,
                created_at=m.created_at,
                updated_at=m.updated_at
            )
            for m in reversed(messages)
        ]
        return MessageHistoryResponse(
            conversation_id=conversation_id,
            messages=message_schemas,
            total_count=len(message_schemas)
        )

    async def get_context_messages(self, conversation_id: UUID, node_id: Optional[UUID] = None, max_messages: int = 20) -> List[Dict[str, Any]]:
        """获取上下文消息（DAG遍历）"""
        context_messages = []
        
        if node_id:
            ancestors = await self.message_repo.get_ancestor_messages(node_id)
            context_messages.extend(ancestors)
        
        pinned_messages = await self.message_repo.get_pinned_messages(conversation_id)
        context_messages.extend(pinned_messages)
        
        recent_messages = await self.message_repo.get_conversation_messages_for_context(conversation_id, max_messages)
        context_messages.extend(recent_messages)
        
        unique_messages = {}
        for msg in context_messages:
            if msg.id not in unique_messages:
                unique_messages[msg.id] = msg
        
        sorted_messages = sorted(unique_messages.values(), key=lambda m: m.created_at)
        
        return [
            {
                "role": msg.role,
                "content": msg.summary if msg.is_summarized and msg.summary else msg.content
            }
            for msg in sorted_messages
        ]

    async def chat(self, request: ChatRequest, user_id: Optional[UUID] = None) -> ChatResponse:
        """非流式聊天"""
        provider = await self.provider_repo.get_provider_by_id(request.provider_id)
        if not provider or not provider.enabled:
            raise ValueError("Provider not found or disabled")
        
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = await self.conversation_repo.create_conversation({
                "provider_id": request.provider_id,
                "user_id": user_id,
                "title": request.message[:50] + "..." if len(request.message) > 50 else request.message,
                "system_prompt": request.system_prompt
            })
            conversation_id = conversation.id
        
        user_message = await self.message_repo.create_message({
            "conversation_id": conversation_id,
            "role": "user",
            "content": request.message
        })
        
        await self.conversation_repo.update_last_message_time(conversation_id)
        
        context_messages = await self.get_context_messages(conversation_id, user_message.id, max_messages=20)
        
        response_content = await self._call_ai_provider(
            provider=provider,
            messages=context_messages,
            temperature=request.temperature or provider.temperature,
            max_tokens=request.max_tokens or provider.max_tokens
        )
        
        assistant_message = await self.message_repo.create_message({
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": response_content,
            "parent_id": user_message.id
        })
        
        await self.conversation_repo.update_last_message_time(conversation_id)
        
        return ChatResponse(
            conversation_id=conversation_id,
            message_id=assistant_message.id,
            content=response_content
        )

    async def stream_chat(self, request: ChatRequest, user_id: Optional[UUID] = None) -> AsyncGenerator[StreamChatResponse, None]:
        """流式聊天"""
        provider = await self.provider_repo.get_provider_by_id(request.provider_id)
        if not provider or not provider.enabled:
            raise ValueError("Provider not found or disabled")
        
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = await self.conversation_repo.create_conversation({
                "provider_id": request.provider_id,
                "user_id": user_id,
                "title": request.message[:50] + "..." if len(request.message) > 50 else request.message,
                "system_prompt": request.system_prompt
            })
            conversation_id = conversation.id
        
        user_message = await self.message_repo.create_message({
            "conversation_id": conversation_id,
            "role": "user",
            "content": request.message
        })
        
        await self.conversation_repo.update_last_message_time(conversation_id)
        
        assistant_message = await self.message_repo.create_message({
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": "",
            "parent_id": user_message.id
        })
        
        context_messages = await self.get_context_messages(conversation_id, user_message.id, max_messages=20)
        
        full_content = ""
        async for delta in self._stream_call_ai_provider(
            provider=provider,
            messages=context_messages,
            temperature=request.temperature or provider.temperature,
            max_tokens=request.max_tokens or provider.max_tokens
        ):
            full_content += delta
            yield StreamChatResponse(
                conversation_id=conversation_id,
                message_id=assistant_message.id,
                delta=delta,
                done=False
            )
        
        await self.message_repo.update_message(assistant_message.id, {"content": full_content})
        
        await self.conversation_repo.update_last_message_time(conversation_id)
        
        yield StreamChatResponse(
            conversation_id=conversation_id,
            message_id=assistant_message.id,
            delta="",
            done=True
        )

    async def pin_message(self, conversation_id: UUID, node_id: UUID, pinned: bool) -> Optional[MessageNodeSchema]:
        """置顶/取消置顶消息"""
        message = await self.message_repo.pin_message(node_id, pinned)
        if not message:
            return None
        return MessageNodeSchema(
            id=message.id,
            conversation_id=message.conversation_id,
            content=message.content,
            role=message.role,
            parent_id=message.parent_id,
            root_id=message.root_id,
            pinned=message.pinned,
            tags=list(message.tags) if message.tags else [],
            metadata=message.metadata,
            is_summarized=message.is_summarized,
            summary=message.summary,
            created_at=message.created_at,
            updated_at=message.updated_at
        )

    async def add_tags(self, conversation_id: UUID, node_id: UUID, tags: List[str]) -> Optional[MessageNodeSchema]:
        """添加标签"""
        message = await self.message_repo.add_tags(node_id, tags)
        if not message:
            return None
        return MessageNodeSchema(
            id=message.id,
            conversation_id=message.conversation_id,
            content=message.content,
            role=message.role,
            parent_id=message.parent_id,
            root_id=message.root_id,
            pinned=message.pinned,
            tags=list(message.tags) if message.tags else [],
            metadata=message.metadata,
            is_summarized=message.is_summarized,
            summary=message.summary,
            created_at=message.created_at,
            updated_at=message.updated_at
        )

    async def summarize_message(self, conversation_id: UUID, node_id: UUID) -> Optional[MessageNodeSchema]:
        """总结消息"""
        message = await self.message_repo.get_message_by_id(node_id)
        if not message:
            return None
        
        provider = await self.provider_repo.get_provider_by_id(message.conversation.provider_id)
        if not provider:
            return None
        
        summary = await self._call_ai_provider(
            provider=provider,
            messages=[
                {"role": "system", "content": "请简要总结以下内容的要点，不超过50字："},
                {"role": message.role, "content": message.content}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        updated_message = await self.message_repo.set_summary(node_id, summary)
        if not updated_message:
            return None
        
        return MessageNodeSchema(
            id=updated_message.id,
            conversation_id=updated_message.conversation_id,
            content=updated_message.content,
            role=updated_message.role,
            parent_id=updated_message.parent_id,
            root_id=updated_message.root_id,
            pinned=updated_message.pinned,
            tags=list(updated_message.tags) if updated_message.tags else [],
            metadata=updated_message.metadata,
            is_summarized=updated_message.is_summarized,
            summary=updated_message.summary,
            created_at=updated_message.created_at,
            updated_at=updated_message.updated_at
        )

    async def _call_ai_provider(
        self,
        provider: AIProvider,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """调用AI提供商"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if provider.provider_type == "openai":
            headers["Authorization"] = f"Bearer {provider.api_key}"
            endpoint = f"{provider.api_endpoint}/chat/completions"
            payload = {
                "model": provider.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        elif provider.provider_type == "anthropic":
            headers["x-api-key"] = provider.api_key
            headers["anthropic-version"] = "2023-06-01"
            endpoint = f"{provider.api_endpoint}/messages"
            payload = {
                "model": provider.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        elif provider.provider_type == "azure":
            headers["api-key"] = provider.api_key
            endpoint = f"{provider.api_endpoint}/chat/completions?api-version=2024-02-01"
            payload = {
                "model": provider.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        else:
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            
            if provider.provider_type == "anthropic":
                return data["content"][0]["text"]
            else:
                return data["choices"][0]["message"]["content"]

    async def _stream_call_ai_provider(
        self,
        provider: AIProvider,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """流式调用AI提供商"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if provider.provider_type == "openai":
            headers["Authorization"] = f"Bearer {provider.api_key}"
            endpoint = f"{provider.api_endpoint}/chat/completions"
            payload = {
                "model": provider.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
        elif provider.provider_type == "anthropic":
            headers["x-api-key"] = provider.api_key
            headers["anthropic-version"] = "2023-06-01"
            endpoint = f"{provider.api_endpoint}/messages"
            payload = {
                "model": provider.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
        elif provider.provider_type == "azure":
            headers["api-key"] = provider.api_key
            endpoint = f"{provider.api_endpoint}/chat/completions?api-version=2024-02-01"
            payload = {
                "model": provider.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
        else:
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")
        
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", endpoint, json=payload, headers=headers, timeout=120.0) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        
                        if provider.provider_type == "anthropic":
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        else:
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content