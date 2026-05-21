import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as redis
from jose import JWTError, jwt

from common.settings import settings


class AuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        pass


class JWTAuthProvider(AuthProvider):
    def __init__(self, secret_key: str = None, algorithm: str = "HS256"):
        self.secret_key = secret_key or settings.jwt_secret_key
        self.algorithm = algorithm

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        token = credentials.get("token") or credentials.get("bearer_token")
        if not token:
            return None
        return await self.validate_token(token)

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                return None
            
            return {
                "user_id": user_id,
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "token_type": "jwt",
                "token_id": payload.get("jti", str(uuid.uuid4()))
            }
        except JWTError:
            return None


class CookieAuthProvider(AuthProvider):
    def __init__(self, redis_client: redis.Redis = None, cookie_name: str = "access_token"):
        self.redis_client = redis_client
        self.cookie_name = cookie_name

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cookies = credentials.get("cookies", {})
        token = cookies.get(self.cookie_name)
        if not token:
            return None
        return await self.validate_token(token)

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            return None
        
        cache_key = f"auth:cookie:{token}"
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        return None

    async def cache_token(self, token: str, user_info: Dict[str, Any], expire_seconds: int = 3600):
        if not self.redis_client:
            return
        
        cache_key = f"auth:cookie:{token}"
        await self.redis_client.setex(
            cache_key,
            expire_seconds,
            json.dumps(user_info)
        )

    async def invalidate_token(self, token: str):
        if not self.redis_client:
            return
        
        cache_key = f"auth:cookie:{token}"
        await self.redis_client.delete(cache_key)


class APIKeyAuthProvider(AuthProvider):
    def __init__(self, redis_client: redis.Redis = None):
        self.redis_client = redis_client
        self.prefix = "auth:apikey:"

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        api_key = credentials.get("api_key") or credentials.get("x_api_key")
        if not api_key:
            return None
        return await self.validate_token(api_key)

    async def validate_token(self, api_key: str) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            return None
        
        cache_key = f"{self.prefix}{api_key}"
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        return None

    async def cache_api_key(self, api_key: str, user_info: Dict[str, Any], expire_seconds: int = 86400 * 30):
        if not self.redis_client:
            return
        
        cache_key = f"{self.prefix}{api_key}"
        await self.redis_client.setex(
            cache_key,
            expire_seconds,
            json.dumps(user_info)
        )

    async def invalidate_api_key(self, api_key: str):
        if not self.redis_client:
            return
        
        cache_key = f"{self.prefix}{api_key}"
        await self.redis_client.delete(cache_key)


class AuthResult:
    def __init__(
        self,
        authenticated: bool,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        roles: List[str] = None,
        permissions: List[str] = None,
        error_message: Optional[str] = None,
        auth_type: Optional[str] = None
    ):
        self.authenticated = authenticated
        self.user_id = user_id
        self.username = username
        self.roles = roles or []
        self.permissions = permissions or []
        self.error_message = error_message
        self.auth_type = auth_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authenticated": self.authenticated,
            "user_id": self.user_id,
            "username": self.username,
            "roles": self.roles,
            "permissions": self.permissions,
            "error_message": self.error_message,
            "auth_type": self.auth_type
        }

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or "admin" in self.roles

    def has_role(self, role: str) -> bool:
        return role in self.roles


class UnifiedAuthenticator:
    def __init__(self, redis_client: redis.Redis = None):
        self.redis_client = redis_client
        self.providers: Dict[str, AuthProvider] = {
            "jwt": JWTAuthProvider(),
            "cookie": CookieAuthProvider(redis_client),
            "api_key": APIKeyAuthProvider(redis_client)
        }
        self.cache_ttl = 300

    def add_provider(self, name: str, provider: AuthProvider):
        self.providers[name] = provider

    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        for auth_type, provider in self.providers.items():
            result = await provider.authenticate(credentials)
            if result:
                await self._cache_auth_result(result)
                return AuthResult(
                    authenticated=True,
                    user_id=result.get("user_id"),
                    username=result.get("username"),
                    roles=result.get("roles", []),
                    permissions=result.get("permissions", []),
                    auth_type=auth_type
                )
        
        return AuthResult(authenticated=False, error_message="Authentication failed")

    async def _cache_auth_result(self, result: Dict[str, Any]):
        if not self.redis_client:
            return
        
        user_id = result.get("user_id")
        if not user_id:
            return
        
        cache_key = f"auth:user:{user_id}"
        await self.redis_client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(result)
        )

    async def get_cached_auth(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            return None
        
        cache_key = f"auth:user:{user_id}"
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None

    async def invalidate_cache(self, user_id: str):
        if not self.redis_client:
            return
        
        cache_key = f"auth:user:{user_id}"
        await self.redis_client.delete(cache_key)


class RequestHeaders:
    TRACE_ID = "X-Trace-Id"
    REQUEST_ID = "X-Request-Id"
    CORRELATION_ID = "X-Correlation-Id"
    TIMESTAMP = "X-Timestamp"
    USER_ID = "X-User-Id"
    USER_ROLES = "X-User-Roles"
    USER_PERMISSIONS = "X-User-Permissions"
    AUTH_TYPE = "X-Auth-Type"
    FORWARDED_FOR = "X-Forwarded-For"
    REAL_IP = "X-Real-IP"
    GATEWAY_VERSION = "X-Gateway-Version"


class AuthHandler:
    @staticmethod
    def extract_credentials(
        headers: Dict[str, str],
        cookies: Dict[str, str] = None,
        query_params: Dict[str, str] = None
    ) -> Dict[str, Any]:
        credentials = {
            "headers": headers,
            "cookies": cookies or {},
            "query_params": query_params or {}
        }
        
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            credentials["token"] = auth_header[7:]
        elif auth_header:
            credentials["api_key"] = auth_header
        
        credentials["x_api_key"] = headers.get("x-api-key")
        
        if not credentials.get("token") and not credentials.get("api_key"):
            credentials["api_key"] = query_params.get("api_key") if query_params else None
        
        return credentials

    @staticmethod
    def build_auth_headers(auth_result: AuthResult) -> Dict[str, str]:
        headers = {}
        
        if auth_result.user_id:
            headers[RequestHeaders.USER_ID] = auth_result.user_id
        
        if auth_result.roles:
            headers[RequestHeaders.USER_ROLES] = ",".join(auth_result.roles)
        
        if auth_result.permissions:
            headers[RequestHeaders.USER_PERMISSIONS] = ",".join(auth_result.permissions)
        
        if auth_result.auth_type:
            headers[RequestHeaders.AUTH_TYPE] = auth_result.auth_type
        
        return headers

    @staticmethod
    def generate_trace_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def generate_request_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def generate_correlation_id() -> str:
        return str(uuid.uuid4())