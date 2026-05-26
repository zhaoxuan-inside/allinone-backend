import json
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.forum_service.entities import Post, Comment, PostLike, CommentLike
from src.forum_service.repository import (
    PostRepository,
    CommentRepository,
    PostLikeRepository,
    CommentLikeRepository
)
from src.forum_service.schemas import (
    PostSummary,
    PostDetail,
    PostCreate,
    Comment,
    CommentCreate,
    PostListResponse
)


class ForumService:
    def __init__(self, db_session: AsyncSession, es_client=None, mongo_client=None):
        self.post_repo = PostRepository(db_session)
        self.comment_repo = CommentRepository(db_session)
        self.post_like_repo = PostLikeRepository(db_session)
        self.comment_like_repo = CommentLikeRepository(db_session)
        self.es_client = es_client
        self.mongo_client = mongo_client
        self.mongo_db = mongo_client["forum"] if mongo_client else None
        self.mongo_posts_collection = self.mongo_db["posts"] if self.mongo_db else None

    async def create_post(
        self,
        author_id: UUID,
        author_username: str,
        author_avatar_url: Optional[str],
        title: str,
        content: str,
        tags: Optional[List[str]] = None
    ) -> PostDetail:
        """创建帖子"""
        post_id = uuid4()
        summary = content[:200] + "..." if len(content) > 200 else content
        
        db_post = Post(
            id=post_id,
            title=title,
            summary=summary,
            author_id=author_id,
            author_username=author_username,
            author_avatar_url=author_avatar_url,
            tags=tags or [],
            content_id=str(post_id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.post_repo.create_post(db_post)
        
        if self.mongo_posts_collection:
            await self.mongo_posts_collection.insert_one({
                "content_id": str(post_id),
                "content": content,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        
        if self.es_client:
            await self._index_post(post_id, title, content, summary, tags or [], author_id)
        
        return await self.get_post_detail(post_id)

    async def _index_post(self, post_id: UUID, title: str, content: str, summary: str, tags: List[str], author_id: UUID):
        """将帖子索引到 Elasticsearch"""
        try:
            await self.es_client.index(
                index="forum_posts",
                id=str(post_id),
                document={
                    "post_id": str(post_id),
                    "title": title,
                    "content": content,
                    "summary": summary,
                    "tags": tags,
                    "author_id": str(author_id),
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            pass

    async def search_posts(self, keyword: str, page: int = 1, size: int = 10) -> PostListResponse:
        """搜索帖子"""
        post_ids = []
        
        if self.es_client:
            try:
                response = await self.es_client.search(
                    index="forum_posts",
                    query={
                        "multi_match": {
                            "query": keyword,
                            "fields": ["title^3", "content^2", "summary", "tags"]
                        }
                    },
                    from_=(page - 1) * size,
                    size=size
                )
                post_ids = [hit["_id"] for hit in response["hits"]["hits"]]
            except Exception as e:
                pass
        
        if not post_ids:
            posts, total = await self.post_repo.get_post_summary_list(page, size)
        else:
            posts = await self.post_repo.get_posts_by_ids([UUID(pid) for pid in post_ids])
            total = len(posts)
        
        post_summaries = [
            PostSummary(
                id=post.id,
                title=post.title,
                summary=post.summary,
                author_id=post.author_id,
                author_username=post.author_username,
                author_avatar_url=post.author_avatar_url,
                tags=post.tags or [],
                created_at=post.created_at,
                comment_count=post.comment_count,
                like_count=post.like_count
            )
            for post in posts
        ]
        
        return PostListResponse(
            posts=post_summaries,
            total=total,
            page=page,
            size=size
        )

    async def get_post_summary_list(self, page: int = 1, size: int = 10) -> PostListResponse:
        """获取帖子摘要列表"""
        posts, total = await self.post_repo.get_post_summary_list(page, size)
        
        post_summaries = [
            PostSummary(
                id=post.id,
                title=post.title,
                summary=post.summary,
                author_id=post.author_id,
                author_username=post.author_username,
                author_avatar_url=post.author_avatar_url,
                tags=post.tags or [],
                created_at=post.created_at,
                comment_count=post.comment_count,
                like_count=post.like_count
            )
            for post in posts
        ]
        
        return PostListResponse(
            posts=post_summaries,
            total=total,
            page=page,
            size=size
        )

    async def get_post_detail(self, post_id: UUID) -> Optional[PostDetail]:
        """获取帖子详情"""
        db_post = await self.post_repo.get_post_by_id(post_id)
        if not db_post:
            return None
        
        content = ""
        if self.mongo_posts_collection:
            mongo_post = await self.mongo_posts_collection.find_one({"content_id": str(post_id)})
            if mongo_post:
                content = mongo_post.get("content", "")
        
        return PostDetail(
            id=db_post.id,
            title=db_post.title,
            content=content,
            summary=db_post.summary,
            author_id=db_post.author_id,
            author_username=db_post.author_username,
            author_avatar_url=db_post.author_avatar_url,
            tags=db_post.tags or [],
            created_at=db_post.created_at,
            updated_at=db_post.updated_at,
            comment_count=db_post.comment_count,
            like_count=db_post.like_count
        )

    async def create_comment(
        self,
        post_id: UUID,
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
            post_id=post_id,
            parent_comment_id=parent_comment_id,
            author_id=author_id,
            author_username=author_username,
            author_avatar_url=author_avatar_url,
            content=content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.comment_repo.create_comment(db_comment)
        await self.post_repo.increment_comment_count(post_id)
        
        return Comment(
            id=db_comment.id,
            post_id=db_comment.post_id,
            parent_comment_id=db_comment.parent_comment_id,
            author_id=db_comment.author_id,
            author_username=db_comment.author_username,
            author_avatar_url=db_comment.author_avatar_url,
            content=db_comment.content,
            created_at=db_comment.created_at,
            like_count=db_comment.like_count,
            replies=[]
        )

    async def get_post_comments(self, post_id: UUID) -> List[Comment]:
        """获取帖子评论（带回复）"""
        db_comments = await self.comment_repo.get_comments_by_post_id(post_id)
        
        comment_map = {}
        root_comments = []
        
        for db_comment in db_comments:
            comment = Comment(
                id=db_comment.id,
                post_id=db_comment.post_id,
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

    async def like_post(self, post_id: UUID, user_id: UUID) -> bool:
        """点赞帖子"""
        existing_like = await self.post_like_repo.get_like(post_id, user_id)
        
        if existing_like:
            await self.post_like_repo.delete_like(post_id, user_id)
            await self.post_repo.decrement_like_count(post_id)
            return False
        else:
            like = PostLike(
                id=uuid4(),
                post_id=post_id,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            await self.post_like_repo.create_like(like)
            await self.post_repo.increment_like_count(post_id)
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