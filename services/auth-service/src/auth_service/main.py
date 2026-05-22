from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import redis.asyncio as redis

from common import settings
from common.config_center import ConfigCenter
from common.logger import UnifiedLogger, LogConfig, LogLevel
from common.nacos import NacosServiceRegistry

from auth_service.service import AuthService
from auth_service.router import router as auth_router, set_auth_service

app = FastAPI(
    title="Auth Service",
    description="Authentication Service for AllInOne Platform",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service_registry: NacosServiceRegistry = None
config_center: ConfigCenter = None
auth_service: AuthService = None


@app.on_event("startup")
async def startup():
    global service_registry, config_center, auth_service

    logger_config = LogConfig(
        level=getattr(LogLevel, settings.log_level.upper(), LogLevel.INFO),
        enable=settings.log_enable,
        enable_trace=settings.log_enable_trace,
        filter_users=settings.log_filter_users,
        filter_paths=settings.log_filter_paths,
        filter_methods=settings.log_filter_methods,
    )
    UnifiedLogger.configure(logger_config)

    if settings.use_config_center:
        config_center = ConfigCenter(hosts=settings.zookeeper_hosts)
        await config_center.init()
        await settings.load_from_config_center(config_center)

    redis_client = redis.from_url(settings.redis_url, decode_responses=False)
    await redis_client.ping()

    auth_service = AuthService(redis_client=redis_client)
    set_auth_service(auth_service)

    service_registry = NacosServiceRegistry(
        server_addresses=settings.nacos_server_addresses,
        namespace=settings.nacos_namespace,
        username=settings.nacos_username,
        password=settings.nacos_password
    )
    await service_registry.init()
    await service_registry.register_service(
        service_name="auth-service",
        port=8008
    )

    UnifiedLogger.info("Auth Service started successfully")


@app.on_event("shutdown")
async def shutdown():
    global service_registry, config_center, auth_service

    if service_registry:
        await service_registry.deregister_service(service_name="auth-service")
        await service_registry.close()

    if config_center:
        await config_center.close()

    UnifiedLogger.info("Auth Service shutdown completed")


@app.get("/")
async def root():
    return {"message": "Auth Service"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth-service"}


app.include_router(auth_router, prefix="/api/v1", tags=["auth"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return {"status_code": exc.status_code, "detail": exc.detail}