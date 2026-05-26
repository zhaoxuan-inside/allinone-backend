from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"

    zookeeper_hosts: str = "localhost:2181"
    use_config_center: bool = False

    postgres_user: str = "admin"
    postgres_password: str = "password"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "allinone"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "allinone-group"

    nacos_server_addresses: str = "localhost:8848"
    nacos_namespace: str = "public"
    nacos_username: str = "nacos"
    nacos_password: str = "nacos"
    service_name: str = "service"
    service_port: int = 8000

    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_user: str = "elastic"
    elasticsearch_password: str = ""
    
    mongodb_uri: str = "mongodb://localhost:27017/"

    jwt_secret_key: str = "your-256-bit-secret-key-here-must-be-at-least-32-characters"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    log_level: str = "INFO"
    log_enable: bool = True
    log_enable_trace: bool = True
    log_filter_users: List[str] = []
    log_filter_paths: List[str] = []
    log_filter_methods: List[str] = []

    gateway_version: str = "1.0.0"
    
    rate_limit_enable: bool = True
    rate_limit_rps: int = 100
    rate_limit_rpm: int = 1000
    rate_limit_burst: int = 200
    
    circuit_breaker_enable: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_success_threshold: int = 2
    circuit_breaker_timeout: float = 30.0

    http_max_connections: int = 100
    http_timeout_seconds: float = 30.0
    http_retry_count: int = 3
    http_retry_delay_ms: int = 100
    
    # Session/认证过期时间（秒）- 无操作自动登出时间
    session_ttl_seconds: int = 3600
    
    # API认证时间戳有效期（秒）
    auth_timestamp_ttl: int = 300

    # 邮件配置
    email_host: str = "smtp.example.com"
    email_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = "noreply@example.com"
    email_use_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    async def load_from_config_center(self, config_center):
        configs = await config_center.get_all_configs()
        
        db_config = configs.get("database", {})
        if db_config:
            self.postgres_user = db_config.get("user", self.postgres_user)
            self.postgres_password = db_config.get("password", self.postgres_password)
            self.postgres_host = db_config.get("host", self.postgres_host)
            self.postgres_port = db_config.get("port", self.postgres_port)
            self.postgres_db = db_config.get("db", self.postgres_db)
        
        redis_config = configs.get("redis", {})
        if redis_config:
            self.redis_host = redis_config.get("host", self.redis_host)
            self.redis_port = redis_config.get("port", self.redis_port)
            self.redis_db = redis_config.get("db", self.redis_db)
            self.redis_password = redis_config.get("password", self.redis_password)
        
        nacos_config = configs.get("nacos", {})
        if nacos_config:
            self.nacos_server_addresses = nacos_config.get("server_addresses", self.nacos_server_addresses)
            self.nacos_namespace = nacos_config.get("namespace", self.nacos_namespace)
        
        jwt_config = configs.get("jwt", {})
        if jwt_config:
            self.jwt_secret_key = jwt_config.get("secret_key", self.jwt_secret_key)
            self.jwt_algorithm = jwt_config.get("algorithm", self.jwt_algorithm)
            self.jwt_access_token_expire_minutes = jwt_config.get("access_expire_minutes", self.jwt_access_token_expire_minutes)
            self.jwt_refresh_token_expire_days = jwt_config.get("refresh_expire_days", self.jwt_refresh_token_expire_days)
        
        log_config = configs.get("logging", {})
        if log_config:
            self.log_level = log_config.get("level", self.log_level)
            self.log_enable = log_config.get("enable", self.log_enable)
            self.log_enable_trace = log_config.get("enable_trace", self.log_enable_trace)
            self.log_filter_users = log_config.get("filter_users", self.log_filter_users)
            self.log_filter_paths = log_config.get("filter_paths", self.log_filter_paths)
            self.log_filter_methods = log_config.get("filter_methods", self.log_filter_methods)
        
        rate_limit_config = configs.get("rate_limit", {})
        if rate_limit_config:
            self.rate_limit_enable = rate_limit_config.get("enable", self.rate_limit_enable)
            self.rate_limit_rps = rate_limit_config.get("rps", self.rate_limit_rps)
            self.rate_limit_rpm = rate_limit_config.get("rpm", self.rate_limit_rpm)
            self.rate_limit_burst = rate_limit_config.get("burst", self.rate_limit_burst)
        
        http_config = configs.get("http", {})
        if http_config:
            self.http_max_connections = http_config.get("max_connections", self.http_max_connections)
            self.http_timeout_seconds = http_config.get("timeout_seconds", self.http_timeout_seconds)
            self.http_retry_count = http_config.get("retry_count", self.http_retry_count)
            self.http_retry_delay_ms = http_config.get("retry_delay_ms", self.http_retry_delay_ms)
        
        # Session/认证过期时间 - 从配置中心读取
        session_config = configs.get("session", {})
        if session_config:
            self.session_ttl_seconds = session_config.get("ttl_seconds", self.session_ttl_seconds)
        
        # API认证时间戳有效期 - 从配置中心读取
        auth_config = configs.get("auth", {})
        if auth_config:
            self.auth_timestamp_ttl = auth_config.get("timestamp_ttl", self.auth_timestamp_ttl)


settings = Settings()


def get_settings() -> Settings:
    return settings