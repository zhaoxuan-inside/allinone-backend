import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent / "common" / "src"))
sys.path.append(str(Path(__file__).parent / "services" / "user-service" / "src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
import uuid

from user_service.entities import User
from common.auth import get_password_hash


async def create_admin_user():
    print("开始创建 admin 用户...")
    
    # 数据库连接配置
    database_url = "postgresql+asyncpg://allinone:iPasswd1234@localhost:5432/allinone"
    engine = create_async_engine(database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    admin_username = "admin"
    admin_email = "admin@example.com"
    admin_password = "iPasswd1234"
    
    async with session_maker() as session:
        # 检查 admin 用户是否已存在
        result = await session.execute(select(User).where(User.username == admin_username))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"用户 '{admin_username}' 已存在！")
            print(f"用户 ID: {existing_user.id}")
            print(f"用户名: {existing_user.username}")
            print(f"邮箱: {existing_user.email}")
            print(f"状态: {existing_user.status}")
            return
        
        # 创建新的 admin 用户
        hashed_password = get_password_hash(admin_password)
        admin_user = User(
            id=uuid.uuid4(),
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            nickname="Administrator",
            bio="系统管理员",
            email_verified=True,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(admin_user)
        await session.commit()
        
        print("✅ Admin 用户创建成功！")
        print(f"用户 ID: {admin_user.id}")
        print(f"用户名: {admin_username}")
        print(f"邮箱: {admin_email}")
        print(f"密码: {admin_password}")
        print(f"状态: {admin_user.status}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
