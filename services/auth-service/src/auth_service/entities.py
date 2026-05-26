from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID

from common.database import Base


class AuthClient(Base):
    __tablename__ = "auth_clients"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    client_id = Column(String(50), unique=True, index=True, nullable=False)
    secret_key = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    roles = Column(Text)
    permissions = Column(Text)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthLockedUser(Base):
    __tablename__ = "auth_locked_users"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False)
    locked_at = Column(DateTime, nullable=False)
    reason = Column(Text)
    unlock_token = Column(String(100))
    status = Column(String(20), default="locked")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthApiKey(Base):
    __tablename__ = "auth_api_keys"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    key_id = Column(String(36), unique=True, index=True, nullable=False)
    api_key = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    user_id_type = Column(String(20), nullable=False)
    name = Column(String(100))
    roles = Column(Text)
    permissions = Column(Text)
    expires_at = Column(DateTime)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthRole(Base):
    __tablename__ = "auth_roles"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    priority = Column(Integer, default=1)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthPermission(Base):
    __tablename__ = "auth_permissions"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(50))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthRolePermission(Base):
    __tablename__ = "auth_role_permissions"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    role_id = Column(UUID(as_uuid=True), nullable=False)
    permission_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)