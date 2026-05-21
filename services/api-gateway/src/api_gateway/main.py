import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Optional

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from common import settings
from common.auth import AuthHandler, AuthResult, RequestHeaders
from common.discovery import NacosServiceDiscovery, RoundRobinBalancer
from common.logger import LogConfig, LogLevel, UnifiedLogger
from common.ratelimit import (
    CircuitBreakerConfig,
    RateLimitConfig,
    RateLimitExceededError,
    RateLimiter,
    RateLimitStrategy,
)


class GatewaySettings:
    app_name: str = "api-gateway"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    nacos_server_addresses: str = "nacos:8848"
    nacos_namespace: str = "public"
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    cors_origins: str = "http://localhost:3000,http://localhost:8080"


gateway_settings = GatewaySettings()

app = FastAPI(
    title="AllInOne API Gateway",
    description="API Gateway for AllInOne Platform with Nacos Service Discovery",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=gateway_settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service_discovery: NacosServiceDiscovery = None
balancer = RoundRobinBalancer()
redis_client: redis.Redis = None
rate_limiter: RateLimiter = None
http_client: httpx.AsyncClient = None

service_route_mapping = {
    "/auth": "auth-service",
    "/users": "user-service",
    "/news": "news-service",
    "/tools": "tools-service",
    "/ai": "ai-service",
    "/stocks": "stocks-service",
    "/forum": "forum-service",
    "/system": "system-service",
}

PUBLIC_PATHS = {
    "/",
    "/health",
    "/services",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/health",
}


@app.on_event("startup")
async def startup():
    global service_discovery, redis_client, rate_limiter, http_client
    
    # 初始化日志
    logger_config = LogConfig(
        level=getattr(LogLevel, settings.log_level.upper(), LogLevel.INFO),
        enable=settings.log_enable,
        enable_trace=settings.log_enable_trace,
        filter_users=settings.log_filter_users,
        filter_paths=settings.log_filter_paths,
        filter_methods=settings.log_filter_methods,
    )
    UnifiedLogger.configure(logger_config)
    
    # 初始化 Redis
    redis_client = redis.from_url(settings.redis_url, decode_responses=False)
    await redis_client.ping()
    
    # 初始化限流器
    rate_limit_config = RateLimitConfig(
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        requests_per_second=settings.rate_limit_rps,
        requests_per_minute=settings.rate_limit_rpm,
        burst_size=settings.rate_limit_burst,
    )
    rate_limiter = RateLimiter(redis_client, rate_limit_config)
    
    # 初始化 HTTP 客户端
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout_seconds),
        limits=httpx.Limits(
            max_connections=settings.http_max_connections,
            max_keepalive_connections=settings.http_max_connections // 2
        )
    )
    
    # 初始化服务发现
    service_discovery = NacosServiceDiscovery(
        server_addresses=settings.nacos_server_addresses,
        namespace=settings.nacos_namespace
    )
    await service_discovery.init()
    
    UnifiedLogger.info("API Gateway started successfully")


@app.on_event("shutdown")
async def shutdown():
    global service_discovery, redis_client, http_client
    
    if service_discovery:
        await service_discovery.close()
    if redis_client:
        await redis_client.close()
    if http_client:
        await http_client.aclose()
    
    UnifiedLogger.info("API Gateway shutdown completed")


def _should_skip_auth(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    for public_path in PUBLIC_PATHS:
        if path.startswith(public_path):
            return True
    return False


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"


async def _process_headers(request: Request, auth_result: Optional[AuthResult] = None) -> Dict[str, str]:
    """处理请求头，保留客户端原样，只添加基础跟踪信息"""
    headers = {}
    
    # 1. 先保留客户端传来的所有请求头（过滤敏感头）
    sensitive_headers = {
        "host", "content-length", "content-encoding",
        "connection", "keep-alive", "upgrade",
        "transfer-encoding"
    }
    for key, value in request.headers.items():
        if key.lower() not in sensitive_headers:
            headers[key] = value
    
    # 2. 只添加基础跟踪信息
    trace_id = request.headers.get(RequestHeaders.TRACE_ID) or str(uuid.uuid4())
    request_id = request.headers.get(RequestHeaders.REQUEST_ID) or str(uuid.uuid4())
    correlation_id = request.headers.get(RequestHeaders.CORRELATION_ID) or str(uuid.uuid4())
    
    headers[RequestHeaders.TRACE_ID] = trace_id
    headers[RequestHeaders.REQUEST_ID] = request_id
    headers[RequestHeaders.CORRELATION_ID] = correlation_id
    headers[RequestHeaders.TIMESTAMP] = datetime.utcnow().isoformat()
    headers[RequestHeaders.GATEWAY_VERSION] = settings.gateway_version
    headers[RequestHeaders.FORWARDED_FOR] = _get_client_ip(request)
    headers[RequestHeaders.REAL_IP] = _get_client_ip(request)
    
    # 3. 如果认证成功，只添加 session_id，不添加用户详细信息
    if auth_result and auth_result.token_id:
        headers["X-Session-Id"] = auth_result.token_id
    
    return headers


async def _rate_limit_check(key: str) -> bool:
    if not settings.rate_limit_enable:
        return True
    allowed = await rate_limiter.check_rate_limit(
        key,
        requests_per_second=settings.rate_limit_rps,
        requests_per_minute=settings.rate_limit_rpm
    )
    if not allowed:
        UnifiedLogger.warning(
            f"Rate limit exceeded for key: {key}",
            path="/",
            method="RATE_LIMIT"
        )
        raise RateLimitExceededError(retry_after=60)
    return True


async def _get_service_instance(path: str):
    for prefix, service_name in service_route_mapping.items():
        if path.startswith(prefix):
            instance = await service_discovery.get_instance(service_name, balancer)
            if instance:
                return instance, service_name
            raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")
    return None, None


async def _authenticate_with_auth_service(credentials: Dict[str, str]) -> Optional[AuthResult]:
    """调用 auth-service 进行认证"""
    try:
        instance, service_name = await service_discovery.get_instance("auth-service", balancer)
        if not instance:
            raise HTTPException(status_code=503, detail="Auth Service unavailable")
        
        url = f"http://{instance.ip}:{instance.port}/api/v1/authenticate"
        
        response = await http_client.post(
            url,
            json={
                "token": credentials.get("token"),
                "api_key": credentials.get("api_key"),
                "authorization": credentials.get("authorization")
            }
        )
        
        if response.status_code != 200:
            return None
        
        result_data = response.json()
        
        if not result_data.get("authenticated"):
            return None
        
        return AuthResult(
            authenticated=True,
            user_id=result_data.get("user_id"),
            username=result_data.get("username"),
            roles=result_data.get("roles", []),
            permissions=result_data.get("permissions", []),
            auth_type=result_data.get("auth_type")
        )
    
    except Exception as e:
        UnifiedLogger.error(f"Auth service call failed: {str(e)}", exc=e)
        return None


@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    path = request.url.path
    start_time = time.monotonic()
    
    trace_id = request.headers.get(RequestHeaders.TRACE_ID) or str(uuid.uuid4())
    UnifiedLogger.set_context(trace_id=trace_id, path=path, method=request.method)
    
    # 限流检查
    try:
        await _rate_limit_check(f"ip:{_get_client_ip(request)}")
    except RateLimitExceededError:
        return Response(
            content='{"error": "Rate limit exceeded", "code": 429}',
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": "60"}
        )
    
    # 认证
    auth_result: Optional[AuthResult] = None
    if not _should_skip_auth(path):
        credentials = AuthHandler.extract_credentials(
            headers=dict(request.headers),
            query_params=dict(request.query_params)
        )
        
        # 调用 auth-service 进行认证
        auth_result = await _authenticate_with_auth_service(credentials)
        
        if not auth_result or not auth_result.authenticated:
            UnifiedLogger.warning(
                f"Authentication failed for path: {path}",
                path=path,
                method=request.method
            )
            return Response(
                content='{"error": "Unauthorized", "code": 401}',
                status_code=401,
                media_type="application/json"
            )
        
        UnifiedLogger.set_context(user_id=auth_result.user_id)
    
    # 处理请求头
    processed_headers = await _process_headers(request, auth_result)
    
    # 如果是公开路径，直接走内部路由
    if _should_skip_auth(path):
        return await call_next(request)
    
    # 否则，转发请求
    instance, service_name = await _get_service_instance(path)
    if not instance:
        return Response(
            content='{"error": "Service not found", "code": 404}',
            status_code=404,
            media_type="application/json"
        )
    
    target_url = f"http://{instance.ip}:{instance.port}{path}"
    content = await request.body()
    
    # 转发请求
    for attempt in range(settings.http_retry_count):
        try:
            response = await http_client.request(
                method=request.method,
                url=target_url,
                headers=processed_headers,
                content=content,
                params=dict(request.query_params)
            )
            
            if response.status_code < 500:
                UnifiedLogger.log_response(
                    request.method, path, response.status_code,
                    duration_ms=(time.monotonic() - start_time) * 1000
                )
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            if attempt < settings.http_retry_count - 1:
                await asyncio.sleep(settings.http_retry_delay_ms / 1000)
                continue
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        
        except httpx.TimeoutException:
            if attempt < settings.http_retry_count - 1:
                await asyncio.sleep(settings.http_retry_delay_ms / 1000)
                continue
            raise HTTPException(status_code=504, detail="Gateway timeout")
        except Exception as e:
            if attempt < settings.http_retry_count - 1:
                await asyncio.sleep(settings.http_retry_delay_ms / 1000)
                continue
            raise HTTPException(status_code=502, detail=f"Bad gateway: {str(e)}")


@app.get("/")
async def root():
    return {"message": "AllInOne API Gateway"}


@app.get("/health")
async def health_check():
    services = []
    for prefix, service_name in service_route_mapping.items():
        try:
            instances = await service_discovery.get_instances(service_name)
            healthy_count = sum(1 for i in instances if i.healthy)
            services.append({
                "service": service_name,
                "status": "healthy" if healthy_count > 0 else "unhealthy",
                "instances": len(instances),
                "healthy_instances": healthy_count
            })
        except Exception as e:
            services.append({
                "service": service_name,
                "status": "error",
                "error": str(e)
            })
    return {"status": "healthy", "services": services}


@app.get("/services")
async def list_services():
    services = []
    for prefix, service_name in service_route_mapping.items():
        instances = await service_discovery.get_instances(service_name)
        services.append({
            "service": service_name,
            "route": prefix,
            "instances": [{"ip": i.ip, "port": i.port, "healthy": i.healthy} for i in instances]
        })
    return {"services": services}


@app.get("/rate-limit/status")
async def rate_limit_status():
    return {
        "enabled": settings.rate_limit_enable,
        "rps": settings.rate_limit_rps,
        "rpm": settings.rate_limit_rpm,
        "burst": settings.rate_limit_burst
    }


@app.post("/rate-limit/reset/{key}")
async def reset_rate_limit(key: str):
    await rate_limiter.reset(key)
    return {"message": f"Rate limit reset for key: {key}"}


@app.get("/circuit-breaker/status/{name}")
async def circuit_breaker_status(name: str):
    cb = rate_limiter.get_circuit_breaker(name)
    return await cb.get_state()
