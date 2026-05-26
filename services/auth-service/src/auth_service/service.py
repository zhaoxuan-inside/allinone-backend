import json
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List

import bcrypt
import redis.asyncio as redis
from jose import jwt

from common import settings
from common.auth import JWTAuthProvider
from common.crypto_utils import md5_hash
from common.logger import UnifiedLogger

from src.auth_service.schemas import (
    CaptchaResponse,
    LoginResponse,
    RegisterResponse,
    ApiAuthResponse,
    PermissionCheckResponse,
    LockAccountResponse,
    UnlockAccountResponse,
    AuthResponse,
    SessionInfo,
    UserSessionListResponse,
    TerminalType
)


class AuthService:
    """认证服务业务逻辑"""

    # Redis Hash Map 定义
    HASH_USERS = "auth:users"
    HASH_SESSIONS = "auth:sessions"
    HASH_TOKENS = "auth:tokens"
    HASH_TERMINALS = "auth:terminals"
    HASH_VERIFICATION = "auth:verification"
    HASH_CAPTCHAS = "auth:captchas"
    HASH_CLIENTS = "auth:clients"
    
    # 独立 Key（用于特殊场景）
    KEY_LOCKED_USER_PREFIX = "auth:locked:"
    KEY_USER_SESSIONS_SET_PREFIX = "auth:user_sessions:"

    TERMINAL_TYPES = ["web", "android", "ios", "h5", "pc"]

    def __init__(self, redis_client: redis.Redis = None):
        self.redis_client = redis_client
        self.jwt_provider = JWTAuthProvider(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

    def _get_cache_ttl(self) -> int:
        """从配置中心获取 TTL，默认为 3600秒（1小时）"""
        return getattr(settings, "session_ttl_seconds", 3600)

    def _get_timestamp_ttl(self) -> int:
        """从配置中心获取时间戳有效期，默认300秒（5分钟）"""
        return getattr(settings, "auth_timestamp_ttl", 300)

    def _generate_captcha(self, length: int = 4) -> str:
        """生成4-6位字符+数字验证码"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """密码验证"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    async def generate_captcha(self) -> CaptchaResponse:
        """生成图形验证码"""
        captcha_id = str(uuid.uuid4())
        captcha_code = self._generate_captcha(random.randint(4, 6))

        if self.redis_client:
            await self.redis_client.hset(
                self.HASH_CAPTCHAS,
                captcha_id,
                json.dumps({
                    "code": captcha_code.lower(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
            )
            await self.redis_client.expire(self.HASH_CAPTCHAS, 300)

        return CaptchaResponse(captcha_id=captcha_id, captcha_code=captcha_code)

    async def _verify_captcha(self, captcha_id: str, captcha_code: str) -> bool:
        """验证验证码"""
        if not self.redis_client:
            return False

        data = await self.redis_client.hget(self.HASH_CAPTCHAS, captcha_id)
        if not data:
            return False

        try:
            stored_data = json.loads(data)
            stored_code = stored_data.get("code", "").lower()
            await self.redis_client.hdel(self.HASH_CAPTCHAS, captcha_id)
            return stored_code == captcha_code.lower()
        except:
            return False

    async def register(self, username: str, password: str, email: str,
                       captcha_id: str, captcha_code: str) -> RegisterResponse:
        """用户注册"""
        if not await self._verify_captcha(captcha_id, captcha_code):
            raise ValueError("Invalid captcha")

        user_id = str(uuid.uuid4())
        hashed_password = self._hash_password(password)

        user_info = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password_hash": hashed_password,
            "email_verified": False,
            "status": "pending",
            "roles": ["user"],
            "permissions": ["read"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if self.redis_client:
            await self.redis_client.hset(self.HASH_USERS, user_id, json.dumps(user_info))

        verification_code = self._generate_captcha(6)
        if self.redis_client:
            await self.redis_client.hset(
                self.HASH_VERIFICATION,
                email,
                json.dumps({
                    "code": verification_code,
                    "user_id": user_id,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    "type": "register"
                })
            )
            await self.redis_client.expire(self.HASH_VERIFICATION, 3600)

        return RegisterResponse(
            user_id=user_id,
            username=username,
            email=email,
            registered_at=datetime.now(timezone.utc),
            verification_sent=True
        )

    async def login(self, username: str, password: str, captcha_id: str,
                    captcha_code: str, terminal_type: str) -> LoginResponse:
        """用户登录"""
        if terminal_type not in self.TERMINAL_TYPES:
            raise ValueError(f"Invalid terminal type: {terminal_type}")

        if not await self._verify_captcha(captcha_id, captcha_code):
            raise ValueError("Invalid captcha")

        if not self.redis_client:
            raise ValueError("Redis not available")

        user_data = None
        user_id = None

        keys = await self.redis_client.hkeys(self.HASH_USERS)
        for key in keys:
            data = await self.redis_client.hget(self.HASH_USERS, key)
            if data:
                user = json.loads(data)
                if user.get("username") == username or user.get("email") == username:
                    user_data = user
                    user_id = key.decode() if isinstance(key, bytes) else str(key)
                    break

        if not user_data:
            raise ValueError("Invalid username or password")

        if user_data.get("status") == "locked":
            raise ValueError("Account is locked")

        if user_data.get("email_verified") is False:
            raise ValueError("Email not verified")

        if not self._verify_password(password, user_data.get("password_hash", "")):
            raise ValueError("Invalid username or password")

        await self._kick_old_session(user_id, terminal_type)

        token_result = await self.generate_token(
            user_id=user_id,
            username=user_data.get("username"),
            roles=user_data.get("roles", []),
            permissions=user_data.get("permissions", [])
        )

        session_id = token_result.get("session_id", str(uuid.uuid4()))
        await self._save_terminal_session(user_id, terminal_type, session_id)

        return LoginResponse(
            access_token=token_result["access_token"],
            token_type="bearer",
            expires_at=token_result["expires_at"],
            user_id=user_id,
            username=user_data.get("username"),
            roles=user_data.get("roles", []),
            permissions=user_data.get("permissions", [])
        )

    async def _kick_old_session(self, user_id: str, terminal_type: str):
        """踢掉同类型终端的旧会话"""
        if not self.redis_client:
            return

        terminal_key = f"{user_id}:{terminal_type}"
        old_session_id = await self.redis_client.hget(self.HASH_TERMINALS, terminal_key)

        if old_session_id:
            old_session_id_str = old_session_id.decode() if isinstance(old_session_id, bytes) else str(old_session_id)
            
            await self.redis_client.hdel(self.HASH_SESSIONS, old_session_id_str)
            
            await self.redis_client.srem(self.KEY_USER_SESSIONS_SET_PREFIX + user_id, old_session_id_str)

    async def _save_terminal_session(self, user_id: str, terminal_type: str, session_id: str):
        """保存终端会话映射"""
        if not self.redis_client:
            return

        terminal_key = f"{user_id}:{terminal_type}"
        await self.redis_client.hset(self.HASH_TERMINALS, terminal_key, session_id)
        await self.redis_client.expire(self.HASH_TERMINALS, self._get_cache_ttl())

    async def authenticate_api(self, client_id: str, timestamp: str, signature: str) -> ApiAuthResponse:
        """第三方API认证"""
        if not self.redis_client:
            return ApiAuthResponse(authenticated=False)

        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        request_timestamp = int(timestamp)

        ttl = self._get_timestamp_ttl()
        if abs(current_timestamp - request_timestamp) > ttl:
            return ApiAuthResponse(authenticated=False)

        client_info = await self.redis_client.hget(self.HASH_CLIENTS, client_id)
        if not client_info:
            return ApiAuthResponse(authenticated=False)

        client_data = json.loads(client_info)
        secret_key = client_data.get("secret_key")

        expected_signature = md5_hash(f"{client_id}{secret_key}{timestamp}")
        if expected_signature != signature:
            return ApiAuthResponse(authenticated=False)

        token_result = await self.generate_token(
            user_id=client_id,
            username=client_data.get("name", client_id),
            roles=client_data.get("roles", ["api_client"]),
            permissions=client_data.get("permissions", ["read", "write"])
        )

        return ApiAuthResponse(
            authenticated=True,
            token=token_result["access_token"],
            expires_at=token_result["expires_at"]
        )

    async def check_permission(self, user_id: str, path: str, method: str) -> PermissionCheckResponse:
        """检查用户权限"""
        if not self.redis_client:
            return PermissionCheckResponse(code=500, msg="Redis not available", allowed=False)

        if await self._is_account_locked(user_id):
            return PermissionCheckResponse(code=403, msg="Account is locked", allowed=False)

        user_info = await self.get_cached_user(user_id)
        if not user_info:
            return PermissionCheckResponse(code=401, msg="User not authenticated", allowed=False)

        permissions = user_info.get("permissions", [])
        roles = user_info.get("roles", [])

        if "admin" in roles or "*" in permissions:
            return PermissionCheckResponse(code=200, msg="Permission granted", allowed=True)

        permission_required = self._get_required_permission(path, method)
        if permission_required in permissions:
            return PermissionCheckResponse(code=200, msg="Permission granted", allowed=True)

        return PermissionCheckResponse(code=403, msg="Insufficient permissions", allowed=False)

    def _get_required_permission(self, path: str, method: str) -> str:
        """根据路径和方法获取所需权限"""
        method_permission_map = {
            "GET": "read",
            "POST": "write",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "delete"
        }
        return method_permission_map.get(method, "read")

    async def _is_account_locked(self, user_id: str) -> bool:
        """检查账户是否被锁定"""
        if not self.redis_client:
            return False

        locked_key = f"{self.KEY_LOCKED_USER_PREFIX}{user_id}"
        locked_data = await self.redis_client.get(locked_key)
        return locked_data is not None

    async def lock_account(self, user_id: str, reason: Optional[str] = None) -> LockAccountResponse:
        """锁定账户"""
        if not self.redis_client:
            return LockAccountResponse(success=False, msg="Redis not available")

        locked_data = {
            "user_id": user_id,
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason or "Manual lock",
            "status": "locked"
        }

        await self.redis_client.set(
            f"{self.KEY_LOCKED_USER_PREFIX}{user_id}",
            json.dumps(locked_data)
        )

        session_ids = await self.redis_client.smembers(self.KEY_USER_SESSIONS_SET_PREFIX + user_id)
        for session_id in session_ids:
            session_id_str = session_id.decode() if isinstance(session_id, bytes) else str(session_id)
            await self.redis_client.hdel(self.HASH_SESSIONS, session_id_str)
            await self.redis_client.hdel(self.HASH_TOKENS, session_id_str)

        await self.redis_client.delete(self.KEY_USER_SESSIONS_SET_PREFIX + user_id)

        return LockAccountResponse(success=True, msg="Account locked successfully")

    async def unlock_account(self, user_id: str, email: str, verification_code: str) -> UnlockAccountResponse:
        """解锁账户"""
        if not self.redis_client:
            return UnlockAccountResponse(success=False, msg="Redis not available")

        verification_data = await self.redis_client.hget(self.HASH_VERIFICATION, email)

        if not verification_data:
            return UnlockAccountResponse(success=False, msg="Verification code not found or expired")

        data = json.loads(verification_data)
        if data.get("user_id") != user_id:
            return UnlockAccountResponse(success=False, msg="Invalid verification code")

        if data.get("code") != verification_code:
            return UnlockAccountResponse(success=False, msg="Invalid verification code")

        await self.redis_client.delete(f"{self.KEY_LOCKED_USER_PREFIX}{user_id}")
        await self.redis_client.hdel(self.HASH_VERIFICATION, email)

        return UnlockAccountResponse(success=True, msg="Account unlocked successfully")

    async def send_unlock_verification(self, email: str) -> bool:
        """发送解锁验证码到邮箱"""
        if not self.redis_client:
            return False

        verification_code = self._generate_captcha(6)
        user_data = None

        keys = await self.redis_client.hkeys(self.HASH_USERS)
        for key in keys:
            data = await self.redis_client.hget(self.HASH_USERS, key)
            if data:
                user = json.loads(data)
                if user.get("email") == email:
                    user_data = user
                    break

        if not user_data:
            return False

        user_id = user_data.get("user_id")

        await self.redis_client.hset(
            self.HASH_VERIFICATION,
            email,
            json.dumps({
                "code": verification_code,
                "user_id": user_id,
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "type": "unlock"
            })
        )
        await self.redis_client.expire(self.HASH_VERIFICATION, 3600)

        return True

    async def get_user_sessions(self, user_id: str) -> UserSessionListResponse:
        """获取用户所有会话"""
        sessions = []

        if not self.redis_client:
            return UserSessionListResponse(user_id=user_id, sessions=sessions)

        for terminal_type in self.TERMINAL_TYPES:
            terminal_key = f"{user_id}:{terminal_type}"
            session_id = await self.redis_client.hget(self.HASH_TERMINALS, terminal_key)
            if session_id:
                session_id_str = session_id.decode() if isinstance(session_id, bytes) else str(session_id)
                session_data = await self.redis_client.hget(self.HASH_SESSIONS, session_id_str)
                if session_data:
                    data = json.loads(session_data)
                    sessions.append(SessionInfo(
                        session_id=session_id_str,
                        user_id=user_id,
                        terminal_type=terminal_type,
                        login_time=datetime.fromisoformat(data.get("login_time", "")),
                        last_active_time=datetime.fromisoformat(data.get("login_time", "")),
                        status="active"
                    ))

        return UserSessionListResponse(user_id=user_id, sessions=sessions)

    async def authenticate(
        self,
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        authorization: Optional[str] = None
    ) -> AuthResponse:
        """统一认证入口"""
        credential = None
        auth_type = None

        if authorization:
            if authorization.lower().startswith("bearer "):
                credential = authorization[7:]
                auth_type = "jwt"
            else:
                credential = authorization
                auth_type = "api_key"
        elif token:
            credential = token
            auth_type = "jwt"
        elif api_key:
            credential = api_key
            auth_type = "api_key"

        if not credential:
            return AuthResponse(
                authenticated=False,
                error="No authentication credentials provided"
            )

        if auth_type == "jwt":
            return await self._authenticate_jwt(credential)
        elif auth_type == "api_key":
            return await self._authenticate_api_key(credential)
        else:
            return AuthResponse(
                authenticated=False,
                error=f"Unsupported auth type: {auth_type}"
            )

    async def _authenticate_jwt(self, token: str) -> AuthResponse:
        """JWT 认证"""
        try:
            session_id = None
            
            if self.redis_client:
                session_id_bytes = await self.redis_client.hget(self.HASH_TOKENS, token)
                if session_id_bytes:
                    session_id = session_id_bytes.decode() if isinstance(session_id_bytes, bytes) else str(session_id_bytes)

            cached_data = None
            if session_id and self.redis_client:
                session_data = await self.redis_client.hget(self.HASH_SESSIONS, session_id)
                if session_data:
                    cached_data = json.loads(session_data)

            if not cached_data:
                user_info = await self.jwt_provider.validate_token(token)
                if not user_info:
                    return AuthResponse(
                        authenticated=False,
                        error="Invalid or expired token"
                    )
                cached_data = user_info

            user_id = cached_data.get("user_id") or cached_data.get("sub")
            if user_id and await self._is_account_locked(user_id):
                return AuthResponse(
                    authenticated=False,
                    error="Account is locked"
                )

            new_session_id = str(uuid.uuid4())
            await self._cache_user_auth(cached_data, token, "jwt", new_session_id)

            return AuthResponse(
                authenticated=True,
                user_id=user_id,
                username=cached_data.get("username"),
                roles=cached_data.get("roles", []),
                permissions=cached_data.get("permissions", []),
                auth_type="jwt",
                token_id=new_session_id
            )

        except Exception as e:
            UnifiedLogger.error(f"JWT authentication failed: {str(e)}", exc=e)
            return AuthResponse(
                authenticated=False,
                error=f"Authentication error: {str(e)}"
            )

    async def _authenticate_api_key(self, api_key: str) -> AuthResponse:
        """API Key 认证"""
        try:
            if not self.redis_client:
                return AuthResponse(
                    authenticated=False,
                    error="Redis not available"
                )

            session_id_bytes = await self.redis_client.hget(self.HASH_TOKENS, api_key)
            if session_id_bytes:
                session_id = session_id_bytes.decode() if isinstance(session_id_bytes, bytes) else str(session_id_bytes)
                session_data = await self.redis_client.hget(self.HASH_SESSIONS, session_id)
                if session_data:
                    user_info = json.loads(session_data)
                    
                    user_id = user_info.get("user_id")
                    if user_id and await self._is_account_locked(user_id):
                        return AuthResponse(
                            authenticated=False,
                            error="Account is locked"
                        )

                    new_session_id = str(uuid.uuid4())
                    await self._cache_user_auth(user_info, api_key, "api_key", new_session_id)

                    return AuthResponse(
                        authenticated=True,
                        user_id=user_id,
                        username=user_info.get("username"),
                        roles=user_info.get("roles", []),
                        permissions=user_info.get("permissions", []),
                        auth_type="api_key",
                        token_id=new_session_id
                    )

            return AuthResponse(
                authenticated=False,
                error="Invalid API key"
            )

        except Exception as e:
            UnifiedLogger.error(f"API Key authentication failed: {str(e)}", exc=e)
            return AuthResponse(
                authenticated=False,
                error=f"Authentication error: {str(e)}"
            )

    async def _cache_user_auth(
        self,
        user_info: Dict,
        credentials: str,
        auth_type: str,
        session_id: str
    ):
        """缓存用户认证信息到 Redis Hash Map"""
        if not self.redis_client:
            return

        ttl = self._get_cache_ttl()

        session_info = {
            **user_info,
            "session_id": session_id,
            "auth_type": auth_type,
            "login_time": datetime.now(timezone.utc).isoformat()
        }

        await self.redis_client.hset(self.HASH_SESSIONS, session_id, json.dumps(session_info))
        await self.redis_client.expire(self.HASH_SESSIONS, ttl)

        await self.redis_client.hset(self.HASH_TOKENS, credentials, session_id)
        await self.redis_client.expire(self.HASH_TOKENS, ttl)

        user_id = user_info.get("user_id") or user_info.get("sub")
        if user_id:
            await self.redis_client.sadd(self.KEY_USER_SESSIONS_SET_PREFIX + user_id, session_id)
            await self.redis_client.expire(self.KEY_USER_SESSIONS_SET_PREFIX + user_id, ttl)

    async def generate_token(
        self,
        user_id: str,
        username: Optional[str] = None,
        roles: Optional[list] = None,
        permissions: Optional[list] = None,
        expire_minutes: Optional[int] = None
    ):
        """生成 JWT Token"""
        if expire_minutes is None:
            expire_minutes = settings.jwt_access_token_expire_minutes

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expire_minutes)

        payload = {
            "sub": user_id,
            "user_id": user_id,
            "username": username,
            "roles": roles or [],
            "permissions": permissions or [],
            "exp": expires_at,
            "iat": now,
            "jti": str(uuid.uuid4())
        }

        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        session_id = str(uuid.uuid4())
        await self._cache_user_auth(payload, token, "jwt", session_id)

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at,
            "session_id": session_id
        }

    async def generate_api_key(
        self,
        user_id: str,
        username: Optional[str] = None,
        roles: Optional[list] = None,
        permissions: Optional[list] = None,
        expire_days: Optional[int] = 30
    ):
        """生成 API Key"""
        api_key = f"ak_{uuid.uuid4().hex[:32]}"
        key_id = str(uuid.uuid4())
        expire_seconds = expire_days * 86400

        user_info = {
            "user_id": user_id,
            "username": username,
            "roles": roles or [],
            "permissions": permissions or [],
            "key_id": key_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=expire_days)).isoformat()
        }

        if self.redis_client:
            session_id = str(uuid.uuid4())
            await self._cache_user_auth(user_info, api_key, "api_key", session_id)

        return {
            "api_key": api_key,
            "key_id": key_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=expire_days),
            "ttl_seconds": expire_seconds
        }

    async def invalidate_token(self, credentials: str, auth_type: str):
        """使凭证失效"""
        if not self.redis_client:
            return

        session_id_bytes = await self.redis_client.hget(self.HASH_TOKENS, credentials)
        if not session_id_bytes:
            return

        session_id = session_id_bytes.decode() if isinstance(session_id_bytes, bytes) else str(session_id_bytes)

        await self.redis_client.hdel(self.HASH_TOKENS, credentials)

        session_data = await self.redis_client.hget(self.HASH_SESSIONS, session_id)
        if session_data:
            user_info = json.loads(session_data)
            user_id = user_info.get("user_id") or user_info.get("sub")

            await self.redis_client.hdel(self.HASH_SESSIONS, session_id)

            if user_id:
                await self.redis_client.srem(self.KEY_USER_SESSIONS_SET_PREFIX + user_id, session_id)

    async def get_cached_user(self, user_id: str) -> Optional[Dict]:
        """获取缓存的用户信息"""
        if not self.redis_client:
            return None

        session_ids = await self.redis_client.smembers(self.KEY_USER_SESSIONS_SET_PREFIX + user_id)

        if not session_ids:
            return None

        first_session_id = session_ids.pop()
        session_id_str = first_session_id.decode() if isinstance(first_session_id, bytes) else str(first_session_id)

        data = await self.redis_client.hget(self.HASH_SESSIONS, session_id_str)
        if data:
            return json.loads(data)

        return None

    async def check_health(self) -> Dict:
        """健康检查"""
        cache_connected = False
        if self.redis_client:
            try:
                await self.redis_client.ping()
                cache_connected = True
            except:
                pass

        return {
            "status": "healthy",
            "cache_connected": cache_connected,
            "config_center_connected": False,
            "session_ttl": self._get_cache_ttl(),
            "timestamp": datetime.now(timezone.utc)
        }