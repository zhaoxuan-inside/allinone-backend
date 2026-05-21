from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from news_service.entities import News, Comment, NewsLike, CommentLike, CrawlerConfig


class NewsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_news(self, news: News) -> News:
        self.session.add(news)
        await self.session.commit()
        await self.session.refresh(news)
        return news

    async def get_news_by_id(self, news_id: UUID) -> Optional[News]:
        result = await self.session.execute(select(News).where(News.id == news_id))
        return result.scalar_one_or_none()

    async def get_news_summary_list(
        self, page: int = 1, size: int = 10
    ) -> tuple[List[News], int]:
        offset = (page - 1) * size
        query = select(News).where(News.status == "published").order_by(desc(News.created_at))
        
        total_result = await self.session.execute(select(News).where(News.status == "published"))
        total = len(total_result.all())
        
        result = await self.session.execute(query.offset(offset).limit(size))
        news_list = result.scalars().all()
        
        return list(news_list), total

    async def get_news_by_ids(self, news_ids: List[UUID]) -> List[News]:
        if not news_ids:
            return []
        result = await self.session.execute(select(News).where(News.id.in_(news_ids)))
        return list(result.scalars().all())

    async def update_news(self, news_id: UUID, data: dict) -> Optional[News]:
        stmt = update(News).where(News.id == news_id).values(**data).returning(News)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_news(self, news_id: UUID) -> bool:
        news = await self.get_news_by_id(news_id)
        if news:
            await self.session.delete(news)
            await self.session.commit()
            return True
        return False

    async def increment_comment_count(self, news_id: UUID):
        stmt = update(News).where(News.id == news_id).values(
            comment_count=News.comment_count + 1
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def increment_like_count(self, news_id: UUID):
        stmt = update(News).where(News.id == news_id).values(
            like_count=News.like_count + 1
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def decrement_like_count(self, news_id: UUID):
        stmt = update(News).where(News.id == news_id).values(
            like_count=News.like_count - 1
        )
        await self.session.execute(stmt)
        await self.session.commit()


class CommentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_comment(self, comment: Comment) -> Comment:
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def get_comments_by_news_id(self, news_id: UUID) -> List[Comment]:
        result = await self.session.execute(
            select(Comment)
            .where(Comment.news_id == news_id)
            .where(Comment.status == "visible")
            .order_by(Comment.created_at)
        )
        return list(result.scalars().all())

    async def get_comment_by_id(self, comment_id: UUID) -> Optional[Comment]:
        result = await self.session.execute(select(Comment).where(Comment.id == comment_id))
        return result.scalar_one_or_none()

    async def update_comment(self, comment_id: UUID, data: dict) -> Optional[Comment]:
        stmt = update(Comment).where(Comment.id == comment_id).values(**data).returning(Comment)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_comment(self, comment_id: UUID) -> bool:
        comment = await self.get_comment_by_id(comment_id)
        if comment:
            await self.session.delete(comment)
            await self.session.commit()
            return True
        return False

    async def increment_like_count(self, comment_id: UUID):
        stmt = update(Comment).where(Comment.id == comment_id).values(
            like_count=Comment.like_count + 1
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def decrement_like_count(self, comment_id: UUID):
        stmt = update(Comment).where(Comment.id == comment_id).values(
            like_count=Comment.like_count - 1
        )
        await self.session.execute(stmt)
        await self.session.commit()


class NewsLikeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_like(self, news_id: UUID, user_id: UUID) -> Optional[NewsLike]:
        result = await self.session.execute(
            select(NewsLike).where(NewsLike.news_id == news_id).where(NewsLike.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_like(self, like: NewsLike) -> NewsLike:
        self.session.add(like)
        await self.session.commit()
        await self.session.refresh(like)
        return like

    async def delete_like(self, news_id: UUID, user_id: UUID) -> bool:
        stmt = delete(NewsLike).where(NewsLike.news_id == news_id).where(NewsLike.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0


class CommentLikeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_like(self, comment_id: UUID, user_id: UUID) -> Optional[CommentLike]:
        result = await self.session.execute(
            select(CommentLike)
            .where(CommentLike.comment_id == comment_id)
            .where(CommentLike.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_like(self, like: CommentLike) -> CommentLike:
        self.session.add(like)
        await self.session.commit()
        await self.session.refresh(like)
        return like

    async def delete_like(self, comment_id: UUID, user_id: UUID) -> bool:
        stmt = delete(CommentLike).where(CommentLike.comment_id == comment_id).where(CommentLike.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0


class CrawlerConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_config(self, config: CrawlerConfig) -> CrawlerConfig:
        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def get_config_by_id(self, config_id: UUID) -> Optional[CrawlerConfig]:
        result = await self.session.execute(select(CrawlerConfig).where(CrawlerConfig.id == config_id))
        return result.scalar_one_or_none()

    async def get_all_configs(self) -> List[CrawlerConfig]:
        result = await self.session.execute(select(CrawlerConfig).order_by(CrawlerConfig.name))
        return list(result.scalars().all())

    async def get_enabled_configs(self) -> List[CrawlerConfig]:
        result = await self.session.execute(select(CrawlerConfig).where(CrawlerConfig.enabled == True))
        return list(result.scalars().all())

    async def update_config(self, config_id: UUID, data: dict) -> Optional[CrawlerConfig]:
        stmt = update(CrawlerConfig).where(CrawlerConfig.id == config_id).values(**data).returning(CrawlerConfig)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_config(self, config_id: UUID) -> bool:
        config = await self.get_config_by_id(config_id)
        if config:
            await self.session.delete(config)
            await self.session.commit()
            return True
        return False

    async def update_last_crawl_time(self, config_id: UUID, crawl_time):
        stmt = update(CrawlerConfig).where(CrawlerConfig.id == config_id).values(last_crawl_time=crawl_time)
        await self.session.execute(stmt)
        await self.session.commit()