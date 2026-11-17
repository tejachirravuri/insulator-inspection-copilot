"""Async database engine and session handling.

One engine (connection pool) per process; one AsyncSession per HTTP request, handed to
route handlers through FastAPI's dependency injection. The session is closed when the
request ends, so connections always return to the pool.
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from inspection_copilot.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    # pool_pre_ping checks a connection before use, which avoids errors after the
    # database restarts or a cloud load balancer drops idle connections.
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False lets us read attributes after commit without another query.
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session and always closes it."""
    async with get_sessionmaker()() as session:
        yield session
