from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID

from common.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "user"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    nickname = Column(String(50))
    avatar_url = Column(String(500))
    bio = Column(Text)
    email_verified = Column(Boolean, default=False)
    phone_number = Column(String(20))
    phone_verified = Column(Boolean, default=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "user"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    role_name = Column(String(50), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserPermission(Base):
    __tablename__ = "user_permissions"
    __table_args__ = {"schema": "user"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    permission_name = Column(String(50), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)