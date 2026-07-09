from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings


class Base(DeclarativeBase):
    pass


engine = None
async_session_maker = None


async def init_db():
    """Initialize database engine and create all tables."""
    global engine, async_session_maker
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False, pool_size=10, max_overflow=20)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create all tables
    async with engine.begin() as conn:
        from app.infrastructure.models import Base
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get a database session."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with async_session_maker() as session:
        yield session


async def close_db():
    """Close database connection."""
    global engine
    if engine:
        await engine.dispose()
