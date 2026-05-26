from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import create_access_token, create_refresh_token, get_password_hash, verify_password
from common.exceptions import ConflictException, NotFoundException, UnauthorizedException
from src.user_service.entities import User
from src.user_service.repository import UserRepository
from src.user_service.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse, UserUpdate, UserPublicProfile, CurrentUserResponse


class UserService:
    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)

    async def register(self, user_create: UserCreate) -> UserResponse:
        if await self.repository.get_by_username(user_create.username):
            raise ConflictException("Username already exists")
        if await self.repository.get_by_email(user_create.email):
            raise ConflictException("Email already exists")

        hashed_password = get_password_hash(user_create.password)
        user = User(
            id=uuid4(),
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password,
            nickname=user_create.nickname or user_create.username
        )

        created_user = await self.repository.create(user)
        return UserResponse.from_orm(created_user)

    async def login(self, login_request: LoginRequest) -> TokenResponse:
        user = await self.repository.get_by_username(login_request.username)
        if not user or not verify_password(login_request.password, user.hashed_password):
            raise UnauthorizedException("Invalid username or password")

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.from_orm(user)
        )

    async def get_user(self, user_id: UUID) -> UserResponse:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return UserResponse.from_orm(user)

    async def update_user(self, user_id: UUID, user_update: UserUpdate) -> UserResponse:
        data = user_update.dict(exclude_unset=True)
        updated_user = await self.repository.update(user_id, data)
        if not updated_user:
            raise NotFoundException("User not found")
        return UserResponse.from_orm(updated_user)

    async def delete_user(self, user_id: UUID) -> bool:
        success = await self.repository.delete(user_id)
        if not success:
            raise NotFoundException("User not found")
        return success

    async def get_user_public_profile(self, user_id: UUID) -> UserPublicProfile:
        """获取用户公开信息（用于显示给其他用户）"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return UserPublicProfile.from_orm(user)

    async def get_current_user(self, user_id: UUID, roles: list = None, permissions: list = None) -> CurrentUserResponse:
        """获取当前登录用户信息（包含角色和权限）"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        
        response = CurrentUserResponse.from_orm(user)
        response.roles = roles or []
        response.permissions = permissions or []
        return response