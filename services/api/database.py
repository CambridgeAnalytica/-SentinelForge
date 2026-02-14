"""
Database configuration and session management.
Uses async SQLAlchemy with PostgreSQL.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from config import settings

# Async engine — pool_size/max_overflow are PostgreSQL-only (SQLite uses StaticPool)
_engine_kwargs = {"echo": settings.DEBUG}
if "sqlite" not in settings.DATABASE_URL:
    _engine_kwargs.update(pool_size=20, max_overflow=10, pool_pre_ping=True)

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


async def get_db() -> AsyncSession:
    """Dependency: yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
