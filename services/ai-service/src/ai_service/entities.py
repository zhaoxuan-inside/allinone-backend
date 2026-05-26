from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Float, JSON, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from common.database import Base


class AIProvider(Base):
    __tablename__ = "ai_providers"
    __table_args__ = {"schema": "ai"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(20), nullable=False)  # openai, anthropic, azure, ollama, local
    api_endpoint = Column(String(500), nullable=False)
    api_key = Column(String(500))
    model_name = Column(String(100), nullable=False)
    max_tokens = Column(Integer, default=4096)
    temperature = Column(Float, default=0.7)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {"schema": "ai"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("ai.ai_providers.id"), nullable=False)
    title = Column(String(200))
    system_prompt = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime)

    messages = relationship("MessageNode", back_populates="conversation", cascade="all, delete-orphan")


class MessageNode(Base):
    __tablename__ = "message_nodes"
    __table_args__ = {"schema": "ai"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai.conversations.id"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("ai.message_nodes.id"), nullable=True)
    root_id = Column(UUID(as_uuid=True), ForeignKey("ai.message_nodes.id"), nullable=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    pinned = Column(Boolean, default=False)
    tags = Column(ARRAY(String), default=[])
    message_metadata = Column(JSON)
    is_summarized = Column(Boolean, default=False)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    parent = relationship("MessageNode", remote_side=[id], backref="children", foreign_keys=[parent_id])
    root = relationship("MessageNode", remote_side=[id], foreign_keys=[root_id])

    def get_ancestors(self):
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_all_related_nodes(self):
        related = [self]
        for child in self.children:
            related.extend(child.get_all_related_nodes())
        return related