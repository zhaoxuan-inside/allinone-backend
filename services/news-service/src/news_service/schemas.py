from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class NewsSummary(BaseModel):
    """新闻摘要信息"""
    id: UUID
    title: str
    summary: str
    source: str
    source_url: Optional[str]
    author_id: Optional[UUID]
    author_username: Optional[str]
    author_avatar_url: Optional[str]
    tags: List[str]
    created_at: datetime
    comment_count: int
    like_count: int


class NewsDetail(BaseModel):
    """新闻详情信息"""
    id: UUID
    title: str
    content: str
    summary: str
    source: str
    source_url: Optional[str]
    author_id: Optional[UUID]
    author_username: Optional[str]
    author_avatar_url: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    comment_count: int
    like_count: int


class Comment(BaseModel):
    """评论信息"""
    id: UUID
    news_id: UUID
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


class NewsSearchRequest(BaseModel):
    """搜索请求"""
    keyword: str
    page: int = 1
    size: int = 10


class NewsListResponse(BaseModel):
    """新闻列表响应"""
    news: List[NewsSummary]
    total: int
    page: int
    size: int


class NewsCrawlerConfig(BaseModel):
    """新闻爬虫配置"""
    id: UUID
    name: str
    source_url: str
    rss_url: Optional[str]
    enabled: bool
    crawl_interval_minutes: int
    last_crawl_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class NewsCrawlerConfigCreate(BaseModel):
    """创建爬虫配置请求"""
    name: str
    source_url: str
    rss_url: Optional[str] = None
    enabled: bool = True
    crawl_interval_minutes: int = 60