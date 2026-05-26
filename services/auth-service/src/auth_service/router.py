from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from src.auth_service.service import AuthService
from src.auth_service.schemas import (
    CaptchaResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ApiAuthResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
    LockAccountRequest,
    LockAccountResponse,
    UnlockAccountRequest,
    UnlockAccountResponse,
    AuthResponse,
    TokenGenerateRequest,
    TokenGenerateResponse,
    ApiKeyGenerateRequest,
    ApiKeyGenerateResponse,
    HealthResponse,
    UserSessionListResponse
)

router = APIRouter()

_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """获取认证服务实例"""
    global _auth_service
    if _auth_service is None:
        raise RuntimeError("AuthService not initialized")
    return _auth_service


def set_auth_service(service: AuthService):
    """设置认证服务实例"""
    global _auth_service
    _auth_service = service


@router.get("/captcha", response_model=CaptchaResponse, summary="生成验证码")
async def get_captcha():
    """生成4-6位字符+数字验证码"""
    try:
        service = get_auth_service()
        return await service.generate_captcha()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate captcha: {str(e)}")


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(request: LoginRequest):
    """用户登录（用户名+密码+验证码）"""
    try:
        service = get_auth_service()
        return await service.login(
            username=request.username,
            password=request.password,
            captcha_id=request.captcha_id,
            captcha_code=request.captcha_code,
            terminal_type=request.terminal_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/register", response_model=RegisterResponse, summary="用户注册")
async def register(request: RegisterRequest):
    """用户注册（需要邮箱验证）"""
    try:
        service = get_auth_service()
        return await service.register(
            username=request.username,
            password=request.password,
            email=request.email,
            captcha_id=request.captcha_id,
            captcha_code=request.captcha_code
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/api/auth", response_model=ApiAuthResponse, summary="第三方API认证")
async def api_authenticate(
    x_client_id: str = Header(None, alias="X-client-id"),
    x_timestamp: str = Header(None, alias="X-timestamp"),
    x_signature: str = Header(None, alias="X-signature")
):
    """
    第三方API认证
    请求头参数：
    - X-client-id: 第三方用户标识
    - X-timestamp: 时间戳（秒）
    - X-signature: MD5(client_id + secret_key + timestamp)
    """
    if not x_client_id or not x_timestamp or not x_signature:
        raise HTTPException(status_code=400, detail="Missing required headers")

    try:
        service = get_auth_service()
        return await service.authenticate_api(x_client_id, x_timestamp, x_signature)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API authentication failed: {str(e)}")


@router.post("/permission/check", response_model=PermissionCheckResponse, summary="检查权限")
async def check_permission(request: PermissionCheckRequest):
    """检查用户对指定路径和方法的权限"""
    try:
        service = get_auth_service()
        return await service.check_permission(request.user_id, request.path, request.method)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Permission check failed: {str(e)}")


@router.post("/account/lock", response_model=LockAccountResponse, summary="锁定账户")
async def lock_account(request: LockAccountRequest):
    """锁定账户（紧急锁定）"""
    try:
        service = get_auth_service()
        return await service.lock_account(request.user_id, request.reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lock account failed: {str(e)}")


@router.post("/account/unlock", response_model=UnlockAccountResponse, summary="解锁账户")
async def unlock_account(request: UnlockAccountRequest):
    """解锁账户（使用邮箱验证码）"""
    try:
        service = get_auth_service()
        return await service.unlock_account(
            user_id=request.user_id,
            email=request.email,
            verification_code=request.verification_code
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unlock account failed: {str(e)}")


@router.post("/account/unlock/code", summary="发送解锁验证码")
async def send_unlock_code(email: str):
    """发送解锁验证码到邮箱"""
    try:
        service = get_auth_service()
        success = await service.send_unlock_verification(email)
        if success:
            return {"message": "Verification code sent successfully"}
        else:
            raise HTTPException(status_code=404, detail="Email not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send verification code: {str(e)}")


@router.get("/user/{user_id}/sessions", response_model=UserSessionListResponse, summary="获取用户会话")
async def get_user_sessions(user_id: str):
    """获取用户所有终端会话列表"""
    try:
        service = get_auth_service()
        return await service.get_user_sessions(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@router.post("/authenticate", response_model=AuthResponse, summary="统一认证")
async def authenticate(request: AuthResponse = None,
                       token: Optional[str] = None,
                       authorization: Optional[str] = None):
    """
    统一认证接口
    支持多种认证方式：
    - JWT Token
    - API Key
    - Authorization Header
    """
    try:
        service = get_auth_service()
        result = await service.authenticate(
            token=token,
            api_key=None,
            authorization=authorization
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@router.post("/token/generate", response_model=TokenGenerateResponse, summary="生成JWT Token")
async def generate_token(request: TokenGenerateRequest):
    """生成JWT访问Token"""
    try:
        service = get_auth_service()
        result = await service.generate_token(
            user_id=request.user_id,
            username=request.username,
            roles=request.roles,
            permissions=request.permissions,
            expire_minutes=request.expire_minutes
        )
        return TokenGenerateResponse(
            access_token=result["access_token"],
            token_type="bearer",
            expires_at=result["expires_at"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation error: {str(e)}")


@router.post("/apikey/generate", response_model=ApiKeyGenerateResponse, summary="生成API Key")
async def generate_apikey(request: ApiKeyGenerateRequest):
    """生成API Key"""
    try:
        service = get_auth_service()
        result = await service.generate_api_key(
            user_id=request.user_id,
            username=request.username,
            roles=request.roles,
            permissions=request.permissions,
            expire_days=request.expire_days
        )
        return ApiKeyGenerateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API Key generation error: {str(e)}")


@router.post("/token/invalidate", summary="使Token失效")
async def invalidate_token(token: str, auth_type: str):
    """使指定的Token失效"""
    try:
        service = get_auth_service()
        await service.invalidate_token(token, auth_type)
        return {"message": "Token invalidated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalidation error: {str(e)}")


@router.get("/user/{user_id}", summary="获取缓存的用户信息")
async def get_cached_user(user_id: str):
    """获取缓存的用户信息"""
    try:
        service = get_auth_service()
        user_info = await service.get_cached_user(user_id)
        if user_info:
            return {"user_id": user_id, "user_info": user_info}
        raise HTTPException(status_code=404, detail="User not found in cache")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get user error: {str(e)}")


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """健康检查接口"""
    try:
        service = get_auth_service()
        health = await service.check_health()
        return HealthResponse(**health)
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            error=str(e)
        )