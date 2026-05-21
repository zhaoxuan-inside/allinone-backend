from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db
from common.permissions import Roles, require_role
from common.auth import get_current_user
from user_service.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse, UserUpdate, UserPublicProfile, CurrentUserResponse
from user_service.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse)
async def register(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.register(user_create)


@router.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.login(login_request)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.get_user(user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: UUID, user_update: UserUpdate, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.update_user(user_id, user_update)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID, 
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(Roles.ADMIN))
):
    service = UserService(db)
    await service.delete_user(user_id)
    return {"message": "User deleted successfully"}


@router.get("/{user_id}/profile", response_model=UserPublicProfile)
async def get_user_public_profile(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取用户公开信息（用于显示给其他用户）"""
    service = UserService(db)
    return await service.get_user_public_profile(user_id)


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前登录用户信息（包含角色和权限）"""
    service = UserService(db)
    return await service.get_current_user(
        user_id=UUID(user.get("user_id")),
        roles=user.get("roles", []),
        permissions=user.get("permissions", [])
    )


@router.patch("/me/profile", response_model=CurrentUserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户个人信息"""
    service = UserService(db)
    return await service.update_user(UUID(user.get("user_id")), user_update)