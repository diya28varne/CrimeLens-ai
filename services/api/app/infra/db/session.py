"""Database session and engine factories."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import get_settings


@lru_cache
def get_engine(postgres_url: str | None = None) -> AsyncEngine:
    url = postgres_url or get_settings().postgres_url
    return create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def get_session_factory(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine or get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
