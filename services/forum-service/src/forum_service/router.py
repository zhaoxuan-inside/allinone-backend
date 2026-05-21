from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import get_current_user
from common.database import get_db
from common.permissions import Roles, require_role, require_permission
from forum_service.schemas import (
    PostSummary,
    PostDetail,
    PostCreate,
    Comment,
    CommentCreate,
    PostListResponse
)
from forum_service.service import ForumService

router = APIRouter(prefix="/forum", tags=["forum"])


def get_forum_service(db: AsyncSession = Depends(get_db)) -> ForumService:
    return ForumService(db)


@router.get("/posts", response_model=PostListResponse)
async def get_post_list(
    page: int = 1,
    size: int = 10,
    forum_service: ForumService = Depends(get_forum_service)
):
    """获取帖子摘要列表"""
    return await forum_service.get_post_summary_list(page, size)


@router.get("/posts/search", response_model=PostListResponse)
async def search_posts(
    keyword: str,
    page: int = 1,
    size: int = 10,
    forum_service: ForumService = Depends(get_forum_service)
):
    """搜索帖子"""
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="Keyword is required")
    return await forum_service.search_posts(keyword, page, size)


@router.get("/posts/{post_id}", response_model=PostDetail)
async def get_post_detail(
    post_id: UUID,
    forum_service: ForumService = Depends(get_forum_service)
):
    """获取帖子详情"""
    post = await forum_service.get_post_detail(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts", response_model=PostDetail)
async def create_post(
    post_create: PostCreate,
    user: dict = Depends(require_role(Roles.USER)),
    forum_service: ForumService = Depends(get_forum_service)
):
    """发布帖子（需要登录）"""
    return await forum_service.create_post(
        author_id=UUID(user.get("user_id")),
        author_username=user.get("username"),
        author_avatar_url=user.get("avatar_url"),
        title=post_create.title,
        content=post_create.content,
        tags=post_create.tags
    )


@router.get("/posts/{post_id}/comments", response_model=list[Comment])
async def get_post_comments(
    post_id: UUID,
    forum_service: ForumService = Depends(get_forum_service)
):
    """获取帖子评论"""
    post = await forum_service.get_post_detail(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return await forum_service.get_post_comments(post_id)


@router.post("/posts/{post_id}/comments", response_model=Comment)
async def create_comment(
    post_id: UUID,
    comment_create: CommentCreate,
    user: dict = Depends(require_role(Roles.USER)),
    forum_service: ForumService = Depends(get_forum_service)
):
    """发布评论（需要登录）"""
    post = await forum_service.get_post_detail(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return await forum_service.create_comment(
        post_id=post_id,
        author_id=UUID(user.get("user_id")),
        author_username=user.get("username"),
        author_avatar_url=user.get("avatar_url"),
        content=comment_create.content,
        parent_comment_id=comment_create.parent_comment_id
    )


@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: UUID,
    user: dict = Depends(require_role(Roles.USER)),
    forum_service: ForumService = Depends(get_forum_service)
):
    """点赞帖子（需要登录）"""
    post = await forum_service.get_post_detail(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    liked = await forum_service.like_post(post_id, UUID(user.get("user_id")))
    return {"liked": liked, "like_count": post.like_count + (1 if liked else -1)}


@router.post("/comments/{comment_id}/like")
async def like_comment(
    comment_id: UUID,
    user: dict = Depends(require_role(Roles.USER)),
    forum_service: ForumService = Depends(get_forum_service)
):
    """点赞评论（需要登录）"""
    liked = await forum_service.like_comment(comment_id, UUID(user.get("user_id")))
    return {"liked": liked}