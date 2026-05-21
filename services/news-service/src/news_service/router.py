from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import get_current_user
from common.database import get_db
from common.permissions import Roles, require_role, require_permission
from news_service.schemas import (
    NewsSummary,
    NewsDetail,
    Comment,
    CommentCreate,
    NewsListResponse,
    NewsCrawlerConfig,
    NewsCrawlerConfigCreate
)
from news_service.service import NewsService

router = APIRouter(prefix="/news", tags=["news"])


def get_news_service(db: AsyncSession = Depends(get_db)) -> NewsService:
    return NewsService(db)


@router.get("/", response_model=NewsListResponse)
async def get_news_list(
    page: int = 1,
    size: int = 10,
    news_service: NewsService = Depends(get_news_service)
):
    """获取新闻列表"""
    return await news_service.get_news_summary_list(page, size)


@router.get("/search", response_model=NewsListResponse)
async def search_news(
    keyword: str,
    page: int = 1,
    size: int = 10,
    news_service: NewsService = Depends(get_news_service)
):
    """搜索新闻"""
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="Keyword is required")
    return await news_service.search_news(keyword, page, size)


@router.get("/{news_id}", response_model=NewsDetail)
async def get_news_detail(
    news_id: UUID,
    news_service: NewsService = Depends(get_news_service)
):
    """获取新闻详情"""
    news = await news_service.get_news_detail(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@router.get("/{news_id}/comments", response_model=list[Comment])
async def get_news_comments(
    news_id: UUID,
    news_service: NewsService = Depends(get_news_service)
):
    """获取新闻评论"""
    news = await news_service.get_news_detail(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return await news_service.get_news_comments(news_id)


@router.post("/{news_id}/comments", response_model=Comment)
async def create_comment(
    news_id: UUID,
    comment_create: CommentCreate,
    user: dict = Depends(require_role(Roles.USER)),
    news_service: NewsService = Depends(get_news_service)
):
    """发布评论（需要登录）"""
    news = await news_service.get_news_detail(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    
    return await news_service.create_comment(
        news_id=news_id,
        author_id=UUID(user.get("user_id")),
        author_username=user.get("username"),
        author_avatar_url=user.get("avatar_url"),
        content=comment_create.content,
        parent_comment_id=comment_create.parent_comment_id
    )


@router.post("/{news_id}/like")
async def like_news(
    news_id: UUID,
    user: dict = Depends(require_role(Roles.USER)),
    news_service: NewsService = Depends(get_news_service)
):
    """点赞新闻（需要登录）"""
    news = await news_service.get_news_detail(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    
    liked = await news_service.like_news(news_id, UUID(user.get("user_id")))
    return {"liked": liked, "like_count": news.like_count + (1 if liked else -1)}


@router.post("/comments/{comment_id}/like")
async def like_comment(
    comment_id: UUID,
    user: dict = Depends(require_role(Roles.USER)),
    news_service: NewsService = Depends(get_news_service)
):
    """点赞评论（需要登录）"""
    liked = await news_service.like_comment(comment_id, UUID(user.get("user_id")))
    return {"liked": liked}


@router.post("/crawler/configs", response_model=NewsCrawlerConfig)
async def create_crawler_config(
    config_create: NewsCrawlerConfigCreate,
    _=Depends(require_role(Roles.ADMIN)),
    news_service: NewsService = Depends(get_news_service)
):
    """创建爬虫配置（管理员）"""
    return await news_service.create_crawler_config(config_create)


@router.get("/crawler/configs", response_model=list[NewsCrawlerConfig])
async def get_all_crawler_configs(
    _=Depends(require_role(Roles.ADMIN)),
    news_service: NewsService = Depends(get_news_service)
):
    """获取所有爬虫配置（管理员）"""
    return await news_service.get_all_crawler_configs()


@router.put("/crawler/configs/{config_id}", response_model=NewsCrawlerConfig)
async def update_crawler_config(
    config_id: UUID,
    config_update: NewsCrawlerConfigCreate,
    _=Depends(require_role(Roles.ADMIN)),
    news_service: NewsService = Depends(get_news_service)
):
    """更新爬虫配置（管理员）"""
    data = {
        "name": config_update.name,
        "source_url": config_update.source_url,
        "rss_url": config_update.rss_url,
        "enabled": config_update.enabled,
        "crawl_interval_minutes": config_update.crawl_interval_minutes
    }
    config = await news_service.update_crawler_config(config_id, data)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.delete("/crawler/configs/{config_id}")
async def delete_crawler_config(
    config_id: UUID,
    _=Depends(require_role(Roles.ADMIN)),
    news_service: NewsService = Depends(get_news_service)
):
    """删除爬虫配置（管理员）"""
    success = await news_service.delete_crawler_config(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"message": "Config deleted successfully"}