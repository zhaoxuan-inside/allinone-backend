from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class PostSummary(BaseModel):
    """帖子摘要信息"""
    id: UUID
    title: str
    summary: str
    author_id: UUID
    author_username: str
    author_avatar_url: Optional[str]
    tags: List[str]
    created_at: datetime
    comment_count: int
    like_count: int


class PostDetail(BaseModel):
    """帖子详情信息"""
    id: UUID
    title: str
    content: str
    summary: str
    author_id: UUID
    author_username: str
    author_avatar_url: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    comment_count: int
    like_count: int


class PostCreate(BaseModel):
    """创建帖子请求"""
    title: str
    content: str
    tags: Optional[List[str]] = []


class Comment(BaseModel):
    """评论信息"""
    id: UUID
    post_id: UUID
    parent_comment_id: Optional[UUID]
    author_id: UUID
    author_username: str
    author_avatar_url: Optional[str]
    content: str
    created_at: datetime
    like_count: int
    replies: List['Comment'] = []


class CommentCreate(BaseModel):
    """创建评论请求"""
    content: str
    parent_comment_id: Optional[UUID] = None


class PostSearchRequest(BaseModel):
    """搜索请求"""
    keyword: str
    page: int = 1
    size: int = 10


class PostListResponse(BaseModel):
    """帖子列表响应"""
    posts: List[PostSummary]
    total: int
    page: int
    size: int