from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID

from common.database import Base


class ToolCategory(Base):
    __tablename__ = "tool_categories"
    __table_args__ = {"schema": "tools"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    icon = Column(String(100))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Tool(Base):
    __tablename__ = "tools"
    __table_args__ = {"schema": "tools"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(100))
    category = Column(String(50), nullable=False)
    is_frontend = Column(Boolean, default=True)
    is_backend = Column(Boolean, default=False)
    endpoint = Column(String(500))
    parameters = Column(JSON)
    response_format = Column(JSON)
    enabled = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ToolUsageLog(Base):
    __tablename__ = "tool_usage_logs"
    __table_args__ = {"schema": "tools"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    tool_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True))
    parameters = Column(JSON)
    result = Column(JSON)
    execution_time_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)