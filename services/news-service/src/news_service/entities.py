from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, Integer, ARRAY, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON

from common.database import Base


class News(Base):
    __tablename__ = "news"
    __table_args__ = {"schema": "news"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    summary = Column(Text)
    source = Column(String(100), nullable=False)
    source_url = Column(String(500))
    author_id = Column(UUID(as_uuid=True))
    author_username = Column(String(50))
    author_avatar_url = Column(String(500))
    tags = Column(ARRAY(String))
    content_id = Column(String(36), nullable=False)
    comment_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    status = Column(String(20), default="published")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = {"schema": "news"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    news_id = Column(UUID(as_uuid=True), nullable=False)
    parent_comment_id = Column(UUID(as_uuid=True))
    author_id = Column(UUID(as_uuid=True), nullable=False)
    author_username = Column(String(50), nullable=False)
    author_avatar_url = Column(String(500))
    content = Column(Text, nullable=False)
    like_count = Column(Integer, default=0)
    status = Column(String(20), default="visible")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NewsLike(Base):
    __tablename__ = "news_likes"
    __table_args__ = {"schema": "news"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    news_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommentLike(Base):
    __tablename__ = "comment_likes"
    __table_args__ = {"schema": "news"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    comment_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CrawlerConfig(Base):
    __tablename__ = "crawler_configs"
    __table_args__ = {"schema": "news"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    source_url = Column(String(500), nullable=False)
    rss_url = Column(String(500))
    enabled = Column(Boolean, default=True)
    crawl_interval_minutes = Column(Integer, default=60)
    last_crawl_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)