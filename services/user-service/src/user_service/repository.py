from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_service.entities import User, UserRole, UserPermission


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user_id: UUID, data: dict) -> Optional[User]:
        stmt = update(User).where(User.id == user_id).values(**data).returning(User)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete(self, user_id: UUID) -> bool:
        user = await self.get_by_id(user_id)
        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False

    async def get_user_roles(self, user_id: UUID) -> List[str]:
        result = await self.session.execute(
            select(UserRole.role_name).where(UserRole.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def get_user_permissions(self, user_id: UUID) -> List[str]:
        result = await self.session.execute(
            select(UserPermission.permission_name).where(UserPermission.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def add_user_role(self, user_id: UUID, role_name: str) -> UserRole:
        user_role = UserRole(
            id=UUID(int=0),
            user_id=user_id,
            role_name=role_name
        )
        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)
        return user_role

    async def add_user_permission(self, user_id: UUID, permission_name: str) -> UserPermission:
        user_permission = UserPermission(
            id=UUID(int=0),
            user_id=user_id,
            permission_name=permission_name
        )
        self.session.add(user_permission)
        await self.session.commit()
        await self.session.refresh(user_permission)
        return user_permission