from typing import Optional, List
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update, desc, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.entities import AIProvider, Conversation, MessageNode


class AIProviderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_providers(self, user_id: Optional[UUID] = None) -> List[AIProvider]:
        query = select(AIProvider).where(AIProvider.enabled == True)
        if user_id:
            query = query.where(or_(AIProvider.user_id == user_id, AIProvider.user_id == None))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_provider_by_id(self, provider_id: UUID) -> Optional[AIProvider]:
        result = await self.session.execute(
            select(AIProvider).where(AIProvider.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def create_provider(self, provider_data: dict) -> AIProvider:
        provider = AIProvider(**provider_data)
        self.session.add(provider)
        await self.session.commit()
        await self.session.refresh(provider)
        return provider

    async def update_provider(self, provider_id: UUID, provider_data: dict) -> Optional[AIProvider]:
        await self.session.execute(
            update(AIProvider).where(AIProvider.id == provider_id).values(**provider_data)
        )
        await self.session.commit()
        return await self.get_provider_by_id(provider_id)

    async def delete_provider(self, provider_id: UUID) -> bool:
        result = await self.session.execute(
            update(AIProvider).where(AIProvider.id == provider_id).values(enabled=False)
        )
        await self.session.commit()
        return result.rowcount > 0


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_conversations(self, user_id: Optional[UUID] = None) -> List[Conversation]:
        query = select(Conversation)
        if user_id:
            query = query.where(Conversation.user_id == user_id)
        query = query.order_by(desc(Conversation.last_message_at))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_conversation_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def create_conversation(self, conversation_data: dict) -> Conversation:
        conversation = Conversation(**conversation_data)
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def update_conversation(self, conversation_id: UUID, conversation_data: dict) -> Optional[Conversation]:
        conversation_data["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(**conversation_data)
        )
        await self.session.commit()
        return await self.get_conversation_by_id(conversation_id)

    async def update_last_message_time(self, conversation_id: UUID) -> None:
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=datetime.utcnow())
        )
        await self.session.commit()

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            await self.session.delete(conversation)
            await self.session.commit()
            return True
        return False


class MessageNodeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_messages_by_conversation(
        self,
        conversation_id: UUID,
        max_messages: int = 20,
        include_pinned: bool = True
    ) -> List[MessageNode]:
        query = select(MessageNode).where(MessageNode.conversation_id == conversation_id)
        
        if not include_pinned:
            query = query.where(or_(MessageNode.pinned == True, MessageNode.pinned == False))
        
        query = query.order_by(MessageNode.created_at.desc()).limit(max_messages)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_message_by_id(self, message_id: UUID) -> Optional[MessageNode]:
        result = await self.session.execute(
            select(MessageNode).where(MessageNode.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_root_messages(self, conversation_id: UUID) -> List[MessageNode]:
        result = await self.session.execute(
            select(MessageNode)
            .where(
                and_(
                    MessageNode.conversation_id == conversation_id,
                    MessageNode.parent_id == None
                )
            )
            .order_by(MessageNode.created_at)
        )
        return list(result.scalars().all())

    async def get_child_messages(self, parent_id: UUID) -> List[MessageNode]:
        result = await self.session.execute(
            select(MessageNode)
            .where(MessageNode.parent_id == parent_id)
            .order_by(MessageNode.created_at)
        )
        return list(result.scalars().all())

    async def get_pinned_messages(self, conversation_id: UUID) -> List[MessageNode]:
        result = await self.session.execute(
            select(MessageNode)
            .where(
                and_(
                    MessageNode.conversation_id == conversation_id,
                    MessageNode.pinned == True
                )
            )
            .order_by(MessageNode.created_at)
        )
        return list(result.scalars().all())

    async def get_ancestor_messages(self, message_id: UUID) -> List[MessageNode]:
        ancestors = []
        message = await self.get_message_by_id(message_id)
        
        while message and message.parent_id:
            parent = await self.get_message_by_id(message.parent_id)
            if parent:
                ancestors.append(parent)
                message = parent
            else:
                break
        
        return ancestors

    async def get_conversation_messages_for_context(
        self,
        conversation_id: UUID,
        max_messages: int = 20
    ) -> List[MessageNode]:
        query = (
            select(MessageNode)
            .where(
                and_(
                    MessageNode.conversation_id == conversation_id,
                    or_(
                        MessageNode.pinned == True,
                        MessageNode.is_summarized == False
                    )
                )
            )
            .order_by(desc(MessageNode.created_at))
            .limit(max_messages)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_message(self, message_data: dict) -> MessageNode:
        message = MessageNode(**message_data)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def update_message(self, message_id: UUID, message_data: dict) -> Optional[MessageNode]:
        message_data["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(MessageNode).where(MessageNode.id == message_id).values(**message_data)
        )
        await self.session.commit()
        return await self.get_message_by_id(message_id)

    async def pin_message(self, message_id: UUID, pinned: bool) -> Optional[MessageNode]:
        return await self.update_message(message_id, {"pinned": pinned})

    async def add_tags(self, message_id: UUID, tags: List[str]) -> Optional[MessageNode]:
        message = await self.get_message_by_id(message_id)
        if message:
            existing_tags = list(message.tags) if message.tags else []
            new_tags = list(set(existing_tags + tags))
            return await self.update_message(message_id, {"tags": new_tags})
        return None

    async def set_summary(self, message_id: UUID, summary: str) -> Optional[MessageNode]:
        return await self.update_message(message_id, {
            "summary": summary,
            "is_summarized": True
        })

    async def delete_message(self, message_id: UUID) -> bool:
        result = await self.session.execute(
            update(MessageNode).where(MessageNode.id == message_id).values(is_summarized=True)
        )
        await self.session.commit()
        return result.rowcount > 0