from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import decode_token
from .exceptions import UnauthorizedException

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token")
    
    return {"user_id": user_id}


async def auth_middleware(request: Request, call_next):
    public_paths = ["/users/login", "/users/register", "/health", "/docs", "/redoc", "/openapi.json"]
    
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("Authorization header missing")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid token")
    
    request.state.user_id = payload.get("sub")
    request.state.token_payload = payload
    
    return await call_next(request)