from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from common import settings
from common.config_center import ConfigCenter
from common.database import create_engine, create_session_maker, get_db
from common.logger import UnifiedLogger, LogConfig, LogLevel
from common.nacos import NacosServiceRegistry
from src.system_service.router import router as system_router

app = FastAPI(
    title="System Service",
    description="System Service for AllInOne Platform - Third-party integrations",
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


@app.on_event("startup")
async def startup():
    global service_registry, config_center
    
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
    
    engine = create_engine(settings.database_url)
    create_session_maker(engine)
    
    service_registry = NacosServiceRegistry(
        server_addresses=settings.nacos_server_addresses,
        namespace=settings.nacos_namespace
    )
    await service_registry.init()
    await service_registry.register_service(
        service_name="system-service",
        port=settings.service_port
    )
    
    UnifiedLogger.info("System Service started successfully")


@app.on_event("shutdown")
async def shutdown():
    global service_registry, config_center
    
    if service_registry:
        await service_registry.deregister_service(service_name="system-service")
        await service_registry.close()
    
    if config_center:
        await config_center.close()
    
    UnifiedLogger.info("System Service shutdown completed")


@app.get("/")
async def root():
    return {"message": "System Service"}


app.include_router(system_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {"status_code": exc.status_code, "detail": exc.detail}