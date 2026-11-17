"""Alembic environment, async variant (the app uses asyncpg, so migrations do too)."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from inspection_copilot.config import get_settings
from inspection_copilot.models import Base

target_metadata = Base.metadata


def database_url() -> str:
    # The test suite passes its own URL (a separate test database); otherwise use the app's.
    return context.config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of executing it (`alembic upgrade head --sql`)."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
