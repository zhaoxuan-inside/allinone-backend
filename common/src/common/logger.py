import json
import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogConfig(BaseModel):
    level: LogLevel = LogLevel.INFO
    enable: bool = True
    enable_console: bool = True
    enable_file: bool = False
    file_path: str = "/var/log/allinone/app.log"
    max_file_size: int = 100 * 1024 * 1024
    backup_count: int = 5
    
    enable_trace: bool = True
    enable_request_body: bool = False
    enable_response_body: bool = False
    
    filter_users: List[str] = []
    filter_paths: List[str] = []
    filter_methods: List[str] = []
    
    sensitive_fields: List[str] = ["password", "token", "authorization", "secret", "api_key"]


class LogContext:
    def __init__(self):
        self.trace_id: Optional[str] = None
        self.request_id: Optional[str] = None
        self.correlation_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.path: Optional[str] = None
        self.method: Optional[str] = None
        self.extra: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "path": self.path,
            "method": self.method,
            **self.extra
        }


class UnifiedLogger:
    _instance: Optional["UnifiedLogger"] = None
    _config: LogConfig = LogConfig()
    _loggers: Dict[str, logging.Logger] = {}
    _context: LogContext = LogContext()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def configure(cls, config: LogConfig):
        cls._config = config
        cls._loggers.clear()

    @classmethod
    def get_logger(cls, name: str = "allinone") -> logging.Logger:
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, cls._config.level.value))
            
            if not logger.handlers:
                if cls._config.enable_console:
                    handler = logging.StreamHandler()
                    handler.setLevel(getattr(logging, cls._config.level.value))
                    formatter = logging.Formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s",
                        defaults={"trace_id": ""}
                    )
                    handler.setFormatter(formatter)
                    logger.addHandler(handler)
                
                if cls._config.enable_file:
                    from logging.handlers import RotatingFileHandler
                    handler = RotatingFileHandler(
                        cls._config.file_path,
                        maxBytes=cls._config.max_file_size,
                        backupCount=cls._config.backup_count
                    )
                    handler.setLevel(getattr(logging, cls._config.level.value))
                    logger.addHandler(handler)
            
            cls._loggers[name] = logger
        
        return cls._loggers[name]

    @classmethod
    def set_context(cls, **kwargs):
        for key, value in kwargs.items():
            if hasattr(cls._context, key):
                setattr(cls._context, key, value)

    @classmethod
    def clear_context(cls):
        cls._context = LogContext()

    @classmethod
    def _should_log(cls, path: str = None, method: str = None, user_id: str = None) -> bool:
        if not cls._config.enable:
            return False

        if cls._config.filter_paths and path:
            if any(path.startswith(p) for p in cls._config.filter_paths):
                return False

        if cls._config.filter_methods and method:
            if method.upper() in [m.upper() for m in cls._config.filter_methods]:
                return False

        if cls._config.filter_users and user_id:
            if user_id in cls._config.filter_users:
                return False

        return True

    @classmethod
    def _mask_sensitive(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return data
        
        result = {}
        for key, value in data.items():
            if any(sf in key.lower() for sf in cls._config.sensitive_fields):
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                result[key] = cls._mask_sensitive(value)
            else:
                result[key] = value
        return result

    @classmethod
    def debug(cls, message: str, **kwargs):
        if not cls._should_log(kwargs.get("path"), kwargs.get("method"), kwargs.get("user_id")):
            return
        logger = cls.get_logger(kwargs.get("logger_name", "allinone"))
        cls.set_context(**kwargs)
        extra = {"trace_id": cls._context.trace_id or ""}
        logger.debug(cls._build_message(message), extra=extra)

    @classmethod
    def info(cls, message: str, **kwargs):
        if not cls._should_log(kwargs.get("path"), kwargs.get("method"), kwargs.get("user_id")):
            return
        logger = cls.get_logger(kwargs.get("logger_name", "allinone"))
        cls.set_context(**kwargs)
        extra = {"trace_id": cls._context.trace_id or ""}
        logger.info(cls._build_message(message), extra=extra)

    @classmethod
    def warning(cls, message: str, **kwargs):
        if not cls._should_log(kwargs.get("path"), kwargs.get("method"), kwargs.get("user_id")):
            return
        logger = cls.get_logger(kwargs.get("logger_name", "allinone"))
        cls.set_context(**kwargs)
        extra = {"trace_id": cls._context.trace_id or ""}
        logger.warning(cls._build_message(message), extra=extra)

    @classmethod
    def error(cls, message: str, exc: Exception = None, **kwargs):
        if not cls._should_log(kwargs.get("path"), kwargs.get("method"), kwargs.get("user_id")):
            return
        logger = cls.get_logger(kwargs.get("logger_name", "allinone"))
        cls.set_context(**kwargs)
        extra = {"trace_id": cls._context.trace_id or ""}
        
        if exc:
            message = f"{message}\n{traceback.format_exc()}"
        
        logger.error(cls._build_message(message), extra=extra)

    @classmethod
    def critical(cls, message: str, exc: Exception = None, **kwargs):
        if not cls._should_log(kwargs.get("path"), kwargs.get("method"), kwargs.get("user_id")):
            return
        logger = cls.get_logger(kwargs.get("logger_name", "allinone"))
        cls.set_context(**kwargs)
        extra = {"trace_id": cls._context.trace_id or ""}
        
        if exc:
            message = f"{message}\n{traceback.format_exc()}"
        
        logger.critical(cls._build_message(message), extra=extra)

    @classmethod
    def log_request(cls, method: str, path: str, headers: Dict = None, body: Any = None, **kwargs):
        if not cls._config.enable_trace:
            return
        
        log_data = {
            "type": "request",
            "method": method,
            "path": path,
            "timestamp": datetime.utcnow().isoformat(),
            **cls._context.to_dict()
        }
        
        if headers:
            safe_headers = cls._mask_sensitive(dict(headers))
            log_data["headers"] = safe_headers
        
        if cls._config.enable_request_body and body:
            if isinstance(body, dict):
                log_data["body"] = cls._mask_sensitive(body)
            else:
                log_data["body"] = str(body)
        
        cls.info(json.dumps(log_data), path=path, method=method)

    @classmethod
    def log_response(cls, method: str, path: str, status_code: int, headers: Dict = None, body: Any = None, duration_ms: float = None, **kwargs):
        if not cls._config.enable_trace:
            return
        
        log_data = {
            "type": "response",
            "method": method,
            "path": path,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat(),
            **cls._context.to_dict()
        }
        
        if duration_ms is not None:
            log_data["duration_ms"] = round(duration_ms, 2)
        
        if headers:
            log_data["headers"] = dict(headers)
        
        if cls._config.enable_response_body and body:
            if isinstance(body, dict):
                log_data["body"] = cls._mask_sensitive(body)
            else:
                log_data["body"] = str(body)
        
        level = LogLevel.INFO if status_code < 400 else LogLevel.ERROR
        log_method = getattr(cls, level.value.lower())
        log_method(json.dumps(log_data), path=path, method=method)

    @classmethod
    def _build_message(cls, message: str) -> str:
        parts = [message]
        
        if cls._context.trace_id:
            parts.append(f"[trace_id={cls._context.trace_id}]")
        if cls._context.user_id:
            parts.append(f"[user_id={cls._context.user_id}]")
        if cls._context.request_id:
            parts.append(f"[request_id={cls._context.request_id}]")
        if cls._context.correlation_id:
            parts.append(f"[correlation_id={cls._context.correlation_id}]")
        
        return " ".join(parts)


logger = UnifiedLogger()


async def log_request(method: str, path: str, headers: Dict = None, body: Any = None, **kwargs):
    logger.log_request(method, path, headers, body, **kwargs)


async def log_response(method: str, path: str, status_code: int, headers: Dict = None, body: Any = None, duration_ms: float = None, **kwargs):
    logger.log_response(method, path, status_code, headers, body, duration_ms, **kwargs)


def log_debug(message: str, **kwargs):
    logger.debug(message, **kwargs)


def log_info(message: str, **kwargs):
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    logger.warning(message, **kwargs)


def log_error(message: str, exc: Exception = None, **kwargs):
    logger.error(message, exc, **kwargs)


def log_critical(message: str, exc: Exception = None, **kwargs):
    logger.critical(message, exc, **kwargs)