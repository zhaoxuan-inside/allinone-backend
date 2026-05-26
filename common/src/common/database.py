from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .settings import settings

Base = declarative_base()

_global_session_maker = None


def create_engine(database_url: str = None):
    return create_async_engine(database_url or settings.database_url, echo=True)


def create_session_maker(engine):
    global _global_session_maker
    _global_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _global_session_maker


async def get_db():
    global _global_session_maker
    if _global_session_maker is None:
        raise RuntimeError("Session maker not initialized. Call create_session_maker first.")
    async with _global_session_maker() as session:
        yield session