"""Alembic environment configuration.

Runs migrations using the application's own async SQLAlchemy engine
(`app.db.session.get_engine`) rather than a separate connection string,
so Alembic always targets the same database as the running application.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.base import Base
from app.db.session import get_engine

# Importing the models package registers all ORM models on
# `Base.metadata`, which Alembic's autogenerate needs to detect tables.
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Emits SQL statements to stdout without requiring a live database
    connection. Not used in normal development/CI flow, but kept for
    Alembic API compatibility.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure Alembic's context with a live connection and migrate.

    Args:
        connection: An active synchronous-facing SQLAlchemy connection,
            provided via `AsyncConnection.run_sync`.
    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using the application's async engine.

    Obtains the shared `AsyncEngine` from `app.db.session.get_engine`,
    opens a connection, and delegates to `do_run_migrations` via
    `run_sync`, since Alembic's migration APIs are synchronous.
    """
    connectable: AsyncEngine = get_engine()

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for running migrations against a live database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()