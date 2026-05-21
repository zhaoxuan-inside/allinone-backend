from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update, insert, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from forum_service.entities import Post, Comment, PostLike, CommentLike


class PostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_post(self, post: Post) -> Post:
        self.session.add(post)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def get_post_by_id(self, post_id: UUID) -> Optional[Post]:
        result = await self.session.execute(select(Post).where(Post.id == post_id))
        return result.scalar_one_or_none()

    async def get_post_summary_list(
        self, page: int = 1, size: int = 10
    ) -> tuple[List[Post], int]:
        offset = (page - 1) * size
        query = select(Post).where(Post.status == "published").order_by(desc(Post.created_at))
        
        total_result = await self.session.execute(select(Post).where(Post.status == "published"))
        total = len(total_result.all())
        
        result = await self.session.execute(query.offset(offset).limit(size))
        posts = result.scalars().all()
        
        return list(posts), total

    async def get_posts_by_ids(self, post_ids: List[UUID]) -> List[Post]:
        if not post_ids:
            return []
        result = await self.session.execute(select(Post).where(Post.id.in_(post_ids)))
        return list(result.scalars().all())

    async def update_post(self, post_id: UUID, data: dict) -> Optional[Post]:
        stmt = update(Post).where(Post.id == post_id).values(**data).returning(Post)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_post(self, post_id: UUID) -> bool:
        post = await self.get_post_by_id(post_id)
        if post:
            await self.session.delete(post)
            await self.session.commit()
            return True
        return False

    async def increment_comment_count(self, post_id: UUID):
        stmt = update(Post).where(Post.id == post_id).values(
            comment_count=Post.comment_count + 1
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def increment_like_count(self, post_id: UUID):
        stmt = update(Post).where(Post.id == post_id).values(
            like_count=Post.like_count + 1
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def decrement_like_count(self, post_id: UUID):
        stmt = update(Post).where(Post.id == post_id).values(
            like_count=Post.like_count - 1
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

    async def get_comments_by_post_id(self, post_id: UUID) -> List[Comment]:
        result = await self.session.execute(
            select(Comment)
            .where(Comment.post_id == post_id)
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


class PostLikeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_like(self, post_id: UUID, user_id: UUID) -> Optional[PostLike]:
        result = await self.session.execute(
            select(PostLike).where(PostLike.post_id == post_id).where(PostLike.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_like(self, like: PostLike) -> PostLike:
        self.session.add(like)
        await self.session.commit()
        await self.session.refresh(like)
        return like

    async def delete_like(self, post_id: UUID, user_id: UUID) -> bool:
        stmt = delete(PostLike).where(PostLike.post_id == post_id).where(PostLike.user_id == user_id)
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