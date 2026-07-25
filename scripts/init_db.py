"""数据库初始化脚本 — 创建所有表"""
import asyncio
import sys

async def init():
    from app.infrastructure.database import init_db, close_db
    from app.infrastructure.models import Base
    from app.config.settings import get_settings

    settings = get_settings()
    print(f"Connecting to: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")

    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(settings.database_url, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init())
