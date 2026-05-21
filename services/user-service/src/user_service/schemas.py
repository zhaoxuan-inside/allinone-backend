from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    nickname: Optional[str] = None


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    nickname: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserPublicProfile(BaseModel):
    """公开用户信息（用于显示给其他用户）"""
    id: UUID
    username: str
    nickname: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CurrentUserResponse(BaseModel):
    """当前登录用户信息"""
    id: UUID
    username: str
    email: EmailStr
    nickname: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    role: str
    roles: Optional[list] = []
    permissions: Optional[list] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse