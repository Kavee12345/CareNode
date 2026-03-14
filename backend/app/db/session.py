from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, event
from app.config import settings
from contextlib import asynccontextmanager
from typing import AsyncGenerator

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_with_rls(user_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Yield a DB session with RLS user context set for zero-leak isolation."""
    async with AsyncSessionLocal() as session:
        try:
            # Set PostgreSQL session variable for RLS policies
            await session.execute(
                text("SET LOCAL app.current_user_id = :uid"),
                {"uid": user_id},
            )
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def rls_session(user_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Context manager version of RLS session for use in services."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("SET LOCAL app.current_user_id = :uid"),
                {"uid": user_id},
            )
            yield session
