import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from common import settings
from common.config_center import ConfigCenter
from common.database import create_engine, create_session_maker, get_db
from common.logger import UnifiedLogger, LogConfig, LogLevel
from common.nacos import NacosServiceRegistry
from common.user_session import init_global_session_manager, UserSessionManager
from user_service.router import router as user_router

app = FastAPI(
    title="User Service",
    description="User Service for AllInOne Platform",
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
redis_client: redis.Redis = None
session_manager: UserSessionManager = None


@app.middleware("http")
async def extract_session_middleware(request: Request, call_next):
    """从请求头提取 session_id 并存储到 request.state"""
    session_id = request.headers.get("X-Session-Id")
    request.state.session_id = session_id
    
    if session_id and session_manager:
        # 可选：自动刷新会话有效期
        await session_manager.refresh_session(session_id)
    
    return await call_next(request)


@app.on_event("startup")
async def startup():
    global service_registry, config_center, redis_client, session_manager
    
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
    
    # 初始化 Redis 连接
    redis_client = redis.from_url(settings.redis_url, decode_responses=False)
    await redis_client.ping()
    
    # 初始化用户会话管理器
    init_global_session_manager(redis_client)
    session_manager = UserSessionManager(redis_client)
    
    engine = create_engine(settings.database_url)
    session_maker = create_session_maker(engine)
    app.dependency_overrides[get_db] = lambda: get_db(session_maker)
    
    service_registry = NacosServiceRegistry(
        server_addresses=settings.nacos_server_addresses,
        namespace=settings.nacos_namespace,
        username=settings.nacos_username,
        password=settings.nacos_password
    )
    await service_registry.init()
    await service_registry.register_service(
        service_name="user-service",
        port=settings.service_port
    )
    
    UnifiedLogger.info("User Service started successfully")


@app.on_event("shutdown")
async def shutdown():
    global service_registry, config_center, redis_client
    
    if service_registry:
        await service_registry.deregister_service(service_name="user-service")
        await service_registry.close()
    
    if config_center:
        await config_center.close()
    
    if redis_client:
        await redis_client.close()
    
    UnifiedLogger.info("User Service shutdown completed")


@app.get("/")
async def root():
    return {"message": "User Service"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {"status_code": exc.status_code, "detail": exc.detail}