import json
from typing import Dict, Optional
import redis.asyncio as redis
from pydantic import BaseModel


class UserSession(BaseModel):
    """用户会话信息"""
    user_id: str
    username: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []
    auth_type: str
    session_id: str
    login_time: str
    # 可扩展的用户信息字段
    email: Optional[str] = None
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    extra: Dict = {}


class UserSessionManager:
    """用户会话管理器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """通过 session_id 获取用户会话信息"""
        if not session_id:
            return None
        
        cache_key = f"auth:session:{session_id}"
        data = await self.redis.get(cache_key)
        
        if not data:
            return None
        
        try:
            session_data = json.loads(data)
            return UserSession(**session_data)
        except (json.JSONDecodeError, ValueError):
            return None
    
    async def refresh_session(self, session_id: str, ttl: int = 1800) -> bool:
        """刷新会话有效期"""
        cache_key = f"auth:session:{session_id}"
        exists = await self.redis.exists(cache_key)
        if exists:
            await self.redis.expire(cache_key, ttl)
            return True
        return False
    
    async def invalidate_session(self, session_id: str) -> bool:
        """使会话失效"""
        cache_key = f"auth:session:{session_id}"
        data = await self.redis.get(cache_key)
        
        if not data:
            return False
        
        session_data = json.loads(data)
        user_id = session_data.get("user_id")
        
        # 1. 删除会话信息
        await self.redis.delete(cache_key)
        
        # 2. 从用户的会话列表中删除
        if user_id:
            user_sessions_key = f"auth:user_sessions:{user_id}"
            await self.redis.srem(user_sessions_key, session_id)
        
        return True
    
    async def get_user_sessions(self, user_id: str) -> list[UserSession]:
        """获取用户的所有活跃会话"""
        sessions = []
        user_sessions_key = f"auth:user_sessions:{user_id}"
        session_ids = await self.redis.smembers(user_sessions_key)
        
        if not session_ids:
            return sessions
        
        for session_id in session_ids:
            session_id_str = session_id.decode() if isinstance(session_id, bytes) else str(session_id)
            session = await self.get_session(session_id_str)
            if session:
                sessions.append(session)
        
        return sessions
    
    async def update_session_field(self, session_id: str, field: str, value: any) -> bool:
        """更新会话中的某个字段"""
        cache_key = f"auth:session:{session_id}"
        data = await self.redis.get(cache_key)
        
        if not data:
            return False
        
        try:
            session_data = json.loads(data)
            session_data[field] = value
            await self.redis.setex(
                cache_key,
                await self.redis.ttl(cache_key),
                json.dumps(session_data)
            )
            return True
        except:
            return False


# 全局会话管理器实例（需要在服务启动时初始化）
_global_session_manager: Optional[UserSessionManager] = None


def init_global_session_manager(redis_client: redis.Redis) -> None:
    """初始化全局会话管理器"""
    global _global_session_manager
    _global_session_manager = UserSessionManager(redis_client)


def get_global_session_manager() -> Optional[UserSessionManager]:
    """获取全局会话管理器"""
    return _global_session_manager
