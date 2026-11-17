"""Shared test fixtures.

Unit tests run anywhere. Tests marked `@pytest.mark.db` need a PostgreSQL server with
pgvector (CI provides a service container; locally `docker compose up -d db`). They use a
separate database, `<name>_test`, which is created and migrated automatically, so tests never
see the documents ingested into the development database. Without a server they are skipped.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from inspection_copilot.config import get_settings

ROOT = Path(__file__).resolve().parents[1]


def _test_url() -> URL:
    url = make_url(get_settings().database_url)
    return url.set(database=f"{url.database}_test")


async def _create_database_if_missing(url: URL) -> None:
    # CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT on the server's
    # maintenance database.
    admin = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await admin.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = _test_url()
    try:
        asyncio.run(_create_database_if_missing(url))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")
    rendered = url.render_as_string(hide_password=False)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
    command.upgrade(config, "head")  # the migration itself is tested on every run
    return rendered


@pytest.fixture
async def db_session(test_database_url: str) -> AsyncIterator[AsyncSession]:
    # NullPool + a fresh engine per test: each pytest-asyncio test has its own event loop,
    # and pooled asyncpg connections cannot be shared across loops.
    engine = create_async_engine(test_database_url, poolclass=NullPool)
    async with engine.connect() as conn:
        # Everything the test writes happens inside this transaction and is rolled back,
        # so tests never leave data behind and can run in any order.
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()
