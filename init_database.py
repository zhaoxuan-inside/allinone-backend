import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "common" / "src"))
sys.path.append(str(Path(__file__).parent / "services" / "user-service" / "src"))
sys.path.append(str(Path(__file__).parent / "services" / "forum-service" / "src"))
sys.path.append(str(Path(__file__).parent / "services" / "news-service" / "src"))
sys.path.append(str(Path(__file__).parent / "services" / "ai-service" / "src"))
sys.path.append(str(Path(__file__).parent / "services" / "stocks-service" / "src"))
sys.path.append(str(Path(__file__).parent / "services" / "tools-service" / "src"))
sys.path.append(str(Path(__file__).parent / "services" / "auth-service" / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from common.database import Base


async def create_schema(engine, schema_name):
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))


async def init_database():
    print("Starting database initialization...")
    
    database_url = "postgresql+asyncpg://allinone:iPasswd1234@localhost:5432/allinone"
    engine = create_async_engine(database_url, echo=True)
    
    schemas = ["user", "forum", "news", "ai", "stocks", "tools", "auth"]
    
    for schema in schemas:
        print(f"Creating schema: {schema}")
        await create_schema(engine, schema)
    
    from user_service.entities import User, UserRole, UserPermission
    from forum_service.entities import Post, Comment, PostLike, CommentLike
    from news_service.entities import News, Comment as NewsComment, NewsLike, CommentLike as NewsCommentLike, CrawlerConfig
    from ai_service.entities import AIProvider, Conversation, MessageNode
    from stocks_service.entities import StockStrategy, TradeSignal, StockKLine, StockInfo, StrategyPerformance
    from tools_service.entities import ToolCategory, Tool, ToolUsageLog
    from auth_service.entities import AuthClient, AuthLockedUser, AuthApiKey, AuthRole, AuthPermission, AuthRolePermission
    
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    
    print("Database initialization completed successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())