from datetime import datetime, timedelta
from typing import Optional, List, Dict
from uuid import UUID, uuid4

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.news_service.entities import News, Comment, NewsLike, CommentLike, CrawlerConfig
from src.news_service.repository import (
    NewsRepository,
    CommentRepository,
    NewsLikeRepository,
    CommentLikeRepository,
    CrawlerConfigRepository
)
from src.news_service.schemas import (
    NewsSummary,
    NewsDetail,
    Comment,
    CommentCreate,
    NewsListResponse,
    NewsCrawlerConfig,
    NewsCrawlerConfigCreate
)


class NewsService:
    def __init__(self, db_session: AsyncSession, es_client=None, mongo_client=None):
        self.news_repo = NewsRepository(db_session)
        self.comment_repo = CommentRepository(db_session)
        self.news_like_repo = NewsLikeRepository(db_session)
        self.comment_like_repo = CommentLikeRepository(db_session)
        self.crawler_repo = CrawlerConfigRepository(db_session)
        self.es_client = es_client
        self.mongo_client = mongo_client
        self.mongo_db = mongo_client["news"] if mongo_client else None
        self.mongo_news_collection = self.mongo_db["news"] if self.mongo_db else None
        self.crawler_tasks = {}

    async def create_news(
        self,
        title: str,
        content: str,
        source: str,
        source_url: Optional[str] = None,
        author_id: Optional[UUID] = None,
        author_username: Optional[str] = None,
        author_avatar_url: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> NewsDetail:
        """创建新闻（用于爬虫或管理员发布）"""
        news_id = uuid4()
        summary = content[:200] + "..." if len(content) > 200 else content
        
        db_news = News(
            id=news_id,
            title=title,
            summary=summary,
            source=source,
            source_url=source_url,
            author_id=author_id,
            author_username=author_username,
            author_avatar_url=author_avatar_url,
            tags=tags or [],
            content_id=str(news_id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.news_repo.create_news(db_news)
        
        if self.mongo_news_collection:
            await self.mongo_news_collection.insert_one({
                "content_id": str(news_id),
                "content": content,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        
        if self.es_client:
            await self._index_news(news_id, title, content, summary, source, tags or [], author_id)
        
        return await self.get_news_detail(news_id)

    async def _index_news(self, news_id: UUID, title: str, content: str, summary: str, source: str, tags: List[str], author_id: Optional[UUID]):
        """将新闻索引到 Elasticsearch"""
        try:
            await self.es_client.index(
                index="news_articles",
                id=str(news_id),
                document={
                    "news_id": str(news_id),
                    "title": title,
                    "content": content,
                    "summary": summary,
                    "source": source,
                    "tags": tags,
                    "author_id": str(author_id) if author_id else None,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            pass

    async def search_news(self, keyword: str, page: int = 1, size: int = 10) -> NewsListResponse:
        """搜索新闻"""
        news_ids = []
        
        if self.es_client:
            try:
                response = await self.es_client.search(
                    index="news_articles",
                    query={
                        "multi_match": {
                            "query": keyword,
                            "fields": ["title^3", "content^2", "summary", "source", "tags"]
                        }
                    },
                    from_=(page - 1) * size,
                    size=size
                )
                news_ids = [hit["_id"] for hit in response["hits"]["hits"]]
            except Exception as e:
                pass
        
        if not news_ids:
            news_list, total = await self.news_repo.get_news_summary_list(page, size)
        else:
            news_list = await self.news_repo.get_news_by_ids([UUID(nid) for nid in news_ids])
            total = len(news_list)
        
        news_summaries = [
            NewsSummary(
                id=news.id,
                title=news.title,
                summary=news.summary,
                source=news.source,
                source_url=news.source_url,
                author_id=news.author_id,
                author_username=news.author_username,
                author_avatar_url=news.author_avatar_url,
                tags=news.tags or [],
                created_at=news.created_at,
                comment_count=news.comment_count,
                like_count=news.like_count
            )
            for news in news_list
        ]
        
        return NewsListResponse(
            news=news_summaries,
            total=total,
            page=page,
            size=size
        )

    async def get_news_summary_list(self, page: int = 1, size: int = 10) -> NewsListResponse:
        """获取新闻摘要列表"""
        news_list, total = await self.news_repo.get_news_summary_list(page, size)
        
        news_summaries = [
            NewsSummary(
                id=news.id,
                title=news.title,
                summary=news.summary,
                source=news.source,
                source_url=news.source_url,
                author_id=news.author_id,
                author_username=news.author_username,
                author_avatar_url=news.author_avatar_url,
                tags=news.tags or [],
                created_at=news.created_at,
                comment_count=news.comment_count,
                like_count=news.like_count
            )
            for news in news_list
        ]
        
        return NewsListResponse(
            news=news_summaries,
            total=total,
            page=page,
            size=size
        )

    async def get_news_detail(self, news_id: UUID) -> Optional[NewsDetail]:
        """获取新闻详情"""
        db_news = await self.news_repo.get_news_by_id(news_id)
        if not db_news:
            return None
        
        content = ""
        if self.mongo_news_collection:
            mongo_news = await self.mongo_news_collection.find_one({"content_id": str(news_id)})
            if mongo_news:
                content = mongo_news.get("content", "")
        
        return NewsDetail(
            id=db_news.id,
            title=db_news.title,
            content=content,
            summary=db_news.summary,
            source=db_news.source,
            source_url=db_news.source_url,
            author_id=db_news.author_id,
            author_username=db_news.author_username,
            author_avatar_url=db_news.author_avatar_url,
            tags=db_news.tags or [],
            created_at=db_news.created_at,
            updated_at=db_news.updated_at,
            comment_count=db_news.comment_count,
            like_count=db_news.like_count
        )

    async def create_comment(
        self,
        news_id: UUID,
        author_id: UUID,
        author_username: str,
        author_avatar_url: Optional[str],
        content: str,
        parent_comment_id: Optional[UUID] = None
    ) -> Comment:
        """创建评论"""
        comment_id = uuid4()
        
        db_comment = Comment(
            id=comment_id,
            news_id=news_id,
            parent_comment_id=parent_comment_id,
            author_id=author_id,
            author_username=author_username,
            author_avatar_url=author_avatar_url,
            content=content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.comment_repo.create_comment(db_comment)
        await self.news_repo.increment_comment_count(news_id)
        
        return Comment(
            id=db_comment.id,
            news_id=db_comment.news_id,
            parent_comment_id=db_comment.parent_comment_id,
            author_id=db_comment.author_id,
            author_username=db_comment.author_username,
            author_avatar_url=db_comment.author_avatar_url,
            content=db_comment.content,
            created_at=db_comment.created_at,
            like_count=db_comment.like_count,
            replies=[]
        )

    async def get_news_comments(self, news_id: UUID) -> List[Comment]:
        """获取新闻评论（带回复）"""
        db_comments = await self.comment_repo.get_comments_by_news_id(news_id)
        
        comment_map = {}
        root_comments = []
        
        for db_comment in db_comments:
            comment = Comment(
                id=db_comment.id,
                news_id=db_comment.news_id,
                parent_comment_id=db_comment.parent_comment_id,
                author_id=db_comment.author_id,
                author_username=db_comment.author_username,
                author_avatar_url=db_comment.author_avatar_url,
                content=db_comment.content,
                created_at=db_comment.created_at,
                like_count=db_comment.like_count,
                replies=[]
            )
            comment_map[db_comment.id] = comment
            
            if db_comment.parent_comment_id:
                if db_comment.parent_comment_id in comment_map:
                    comment_map[db_comment.parent_comment_id].replies.append(comment)
            else:
                root_comments.append(comment)
        
        return root_comments

    async def like_news(self, news_id: UUID, user_id: UUID) -> bool:
        """点赞新闻"""
        existing_like = await self.news_like_repo.get_like(news_id, user_id)
        
        if existing_like:
            await self.news_like_repo.delete_like(news_id, user_id)
            await self.news_repo.decrement_like_count(news_id)
            return False
        else:
            like = NewsLike(
                id=uuid4(),
                news_id=news_id,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            await self.news_like_repo.create_like(like)
            await self.news_repo.increment_like_count(news_id)
            return True

    async def like_comment(self, comment_id: UUID, user_id: UUID) -> bool:
        """点赞评论"""
        existing_like = await self.comment_like_repo.get_like(comment_id, user_id)
        
        if existing_like:
            await self.comment_like_repo.delete_like(comment_id, user_id)
            await self.comment_repo.decrement_like_count(comment_id)
            return False
        else:
            like = CommentLike(
                id=uuid4(),
                comment_id=comment_id,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            await self.comment_like_repo.create_like(like)
            await self.comment_repo.increment_like_count(comment_id)
            return True

    async def create_crawler_config(self, config_create: NewsCrawlerConfigCreate) -> NewsCrawlerConfig:
        """创建爬虫配置（管理员）"""
        config = CrawlerConfig(
            id=uuid4(),
            name=config_create.name,
            source_url=config_create.source_url,
            rss_url=config_create.rss_url,
            enabled=config_create.enabled,
            crawl_interval_minutes=config_create.crawl_interval_minutes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.crawler_repo.create_config(config)
        
        if config.enabled:
            await self._start_crawler(config.id)
        
        return NewsCrawlerConfig(
            id=config.id,
            name=config.name,
            source_url=config.source_url,
            rss_url=config.rss_url,
            enabled=config.enabled,
            crawl_interval_minutes=config.crawl_interval_minutes,
            last_crawl_time=config.last_crawl_time,
            created_at=config.created_at,
            updated_at=config.updated_at
        )

    async def get_all_crawler_configs(self) -> List[NewsCrawlerConfig]:
        """获取所有爬虫配置（管理员）"""
        configs = await self.crawler_repo.get_all_configs()
        return [
            NewsCrawlerConfig(
                id=config.id,
                name=config.name,
                source_url=config.source_url,
                rss_url=config.rss_url,
                enabled=config.enabled,
                crawl_interval_minutes=config.crawl_interval_minutes,
                last_crawl_time=config.last_crawl_time,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            for config in configs
        ]

    async def update_crawler_config(self, config_id: UUID, data: dict) -> Optional[NewsCrawlerConfig]:
        """更新爬虫配置（管理员）"""
        config = await self.crawler_repo.update_config(config_id, data)
        if not config:
            return None
        
        old_enabled = data.get("enabled")
        if old_enabled is False and str(config_id) in self.crawler_tasks:
            await self._stop_crawler(config_id)
        elif old_enabled is True:
            await self._start_crawler(config_id)
        
        return NewsCrawlerConfig(
            id=config.id,
            name=config.name,
            source_url=config.source_url,
            rss_url=config.rss_url,
            enabled=config.enabled,
            crawl_interval_minutes=config.crawl_interval_minutes,
            last_crawl_time=config.last_crawl_time,
            created_at=config.created_at,
            updated_at=config.updated_at
        )

    async def delete_crawler_config(self, config_id: UUID) -> bool:
        """删除爬虫配置（管理员）"""
        await self._stop_crawler(config_id)
        return await self.crawler_repo.delete_config(config_id)

    async def _start_crawler(self, config_id: UUID):
        """启动爬虫任务"""
        if str(config_id) in self.crawler_tasks:
            return
        
        async def crawl_task():
            while str(config_id) in self.crawler_tasks:
                config = await self.crawler_repo.get_config_by_id(config_id)
                if not config or not config.enabled:
                    break
                
                await self._execute_crawl(config)
                await self.crawler_repo.update_last_crawl_time(config_id, datetime.utcnow())
                
                await asyncio.sleep(config.crawl_interval_minutes * 60)
        
        self.crawler_tasks[str(config_id)] = asyncio.create_task(crawl_task())

    async def _stop_crawler(self, config_id: UUID):
        """停止爬虫任务"""
        task = self.crawler_tasks.pop(str(config_id), None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _execute_crawl(self, config: CrawlerConfig):
        """执行爬虫抓取（模拟实现）"""
        try:
            if config.rss_url:
                await self._crawl_rss(config)
            else:
                await self._crawl_web(config)
        except Exception as e:
            pass

    async def _crawl_rss(self, config: CrawlerConfig):
        """抓取 RSS 订阅"""
        pass

    async def _crawl_web(self, config: CrawlerConfig):
        """抓取网页内容"""
        pass