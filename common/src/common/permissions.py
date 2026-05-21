from typing import List

from fastapi import Depends, Request

from .middleware import get_current_user
from .exceptions import ForbiddenException


class PermissionChecker:
    def __init__(self, required_permissions: List[str] = None, required_roles: List[str] = None):
        self.required_permissions = required_permissions or []
        self.required_roles = required_roles or []

    async def __call__(self, request: Request, user: dict = Depends(get_current_user)) -> dict:
        user_id = user.get("user_id")
        
        user_roles = await self._get_user_roles(user_id)
        user_permissions = await self._get_user_permissions(user_id)

        if self.required_roles:
            has_role = any(role in user_roles for role in self.required_roles)
            if not has_role:
                raise ForbiddenException("Insufficient role")

        if self.required_permissions:
            has_permission = all(perm in user_permissions for perm in self.required_permissions)
            if not has_permission:
                raise ForbiddenException("Insufficient permission")

        request.state.user_roles = user_roles
        request.state.user_permissions = user_permissions
        
        return user

    async def _get_user_roles(self, user_id: str) -> List[str]:
        return ["user"]

    async def _get_user_permissions(self, user_id: str) -> List[str]:
        return ["read", "write"]


def require_role(*roles: str):
    return PermissionChecker(required_roles=list(roles))


def require_permission(*permissions: str):
    return PermissionChecker(required_permissions=list(permissions))


class Permissions:
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class Roles:
    ADMIN = "admin"
    MANAGER = "manager"
    READER = "reader"
    GUEST = "guest"
    MODERATOR = "moderator"
    USER = "user"


class RolePermissions:
    """各角色对应的权限映射"""
    
    @classmethod
    def get_permissions(cls, role: str) -> List[str]:
        """根据角色获取权限列表"""
        permissions_map = {
            Roles.ADMIN: [Permissions.READ, Permissions.WRITE, Permissions.DELETE, Permissions.ADMIN],
            Roles.MANAGER: [Permissions.READ, Permissions.WRITE],
            Roles.READER: [Permissions.READ],
            Roles.GUEST: [Permissions.READ],
            Roles.MODERATOR: [Permissions.READ, Permissions.WRITE, Permissions.DELETE],
            Roles.USER: [Permissions.READ, Permissions.WRITE]
        }
        return permissions_map.get(role, [Permissions.READ])