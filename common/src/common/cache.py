from redis.asyncio import Redis

from .settings import settings

redis_client = None


def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password if settings.redis_password else None,
            decode_responses=True
        )
    return redis_client