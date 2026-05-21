from datetime import datetime
from typing import Optional, List, Dict, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class CaptchaResponse(BaseModel):
    """验证码响应"""
    captcha_id: str
    captcha_code: str


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str
    captcha_id: str
    captcha_code: str
    terminal_type: str = Field(..., pattern="^(web|android|ios|h5|pc)$")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_id: str
    username: str
    roles: List[str]
    permissions: List[str]


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: EmailStr
    captcha_id: str
    captcha_code: str


class RegisterResponse(BaseModel):
    """注册响应"""
    user_id: str
    username: str
    email: str
    registered_at: datetime
    verification_sent: bool


class ApiAuthRequest(BaseModel):
    """API认证请求（来自请求头）"""
    client_id: str = Field(alias="X-client-id")
    timestamp: str = Field(alias="X-timestamp")
    signature: str = Field(alias="X-signature")


class ApiAuthResponse(BaseModel):
    """API认证响应"""
    authenticated: bool
    token: Optional[str] = None
    expires_at: Optional[datetime] = None


class PermissionCheckRequest(BaseModel):
    """权限检查请求"""
    user_id: str
    path: str
    method: str


class PermissionCheckResponse(BaseModel):
    """权限检查响应"""
    code: int
    msg: str
    allowed: bool


class TerminalType(str):
    """终端类型枚举"""
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"
    H5 = "h5"
    PC = "pc"


class LockAccountRequest(BaseModel):
    """锁定账户请求"""
    user_id: str
    reason: Optional[str] = None


class LockAccountResponse(BaseModel):
    """锁定账户响应"""
    success: bool
    msg: str


class UnlockAccountRequest(BaseModel):
    """解锁账户请求"""
    user_id: str
    email: EmailStr
    verification_code: str


class UnlockAccountResponse(BaseModel):
    """解锁账户响应"""
    success: bool
    msg: str


class AuthResponse(BaseModel):
    """通用认证响应"""
    authenticated: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    roles: Optional[List[str]] = []
    permissions: Optional[List[str]] = []
    auth_type: Optional[str] = None
    token_id: Optional[str] = None
    error: Optional[str] = None


class TokenGenerateRequest(BaseModel):
    """生成Token请求"""
    user_id: str
    username: Optional[str] = None
    roles: Optional[List[str]] = []
    permissions: Optional[List[str]] = []
    expire_minutes: Optional[int] = None


class TokenGenerateResponse(BaseModel):
    """生成Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class ApiKeyGenerateRequest(BaseModel):
    """生成API Key请求"""
    user_id: str
    username: Optional[str] = None
    roles: Optional[List[str]] = []
    permissions: Optional[List[str]] = []
    expire_days: Optional[int] = 30


class ApiKeyGenerateResponse(BaseModel):
    """生成API Key响应"""
    api_key: str
    key_id: str
    expires_at: datetime
    ttl_seconds: int


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    cache_connected: Optional[bool] = None
    config_center_connected: Optional[bool] = None
    session_ttl: Optional[int] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    user_id: str
    terminal_type: str
    login_time: datetime
    last_active_time: datetime
    status: str
    ip_address: Optional[str] = None


class UserSessionListResponse(BaseModel):
    """用户会话列表响应"""
    user_id: str
    sessions: List[SessionInfo]


class AuthRequest(BaseModel):
    """统一认证请求"""
    token: Optional[str] = None
    api_key: Optional[str] = None
    authorization: Optional[str] = None
