from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .settings import settings

Base = declarative_base()


def create_engine(database_url: str = None):
    return create_async_engine(database_url or settings.database_url, echo=True)


def create_session_maker(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db(session_maker):
    async with session_maker() as session:
        yield session