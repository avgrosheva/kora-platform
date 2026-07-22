"""Async database engine and session factory configuration.

This module is responsible for creating the SQLAlchemy `AsyncEngine` and
the `async_sessionmaker` used to produce `AsyncSession` instances
throughout the application. Engine and sessionmaker creation is cached so
they are built exactly once per process and reused everywhere.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_ASYNC_DRIVER_PREFIX = "postgresql+asyncpg://"
_SYNC_DRIVER_PREFIX = "postgresql+psycopg://"


def _get_async_database_url() -> str:
    """Build the async PostgreSQL connection URL.

    `Settings.DATABASE_URL` is expressed using the synchronous
    `postgresql+psycopg` driver scheme. This function derives the
    equivalent asynchronous URL using the `asyncpg` driver, required by
    SQLAlchemy's `AsyncEngine`.

    Returns:
        The PostgreSQL connection URL using the `postgresql+asyncpg`
        driver scheme.

    Raises:
        RuntimeError: If `Settings.DATABASE_URL` is not configured,
            meaning the database integration has not yet been set up.
    """
    settings = get_settings()
    database_url = settings.DATABASE_URL

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set POSTGRES_PASSWORD "
            "(and related POSTGRES_* variables) in your environment "
            "before using the database layer."
        )

    return database_url.replace(_SYNC_DRIVER_PREFIX, _ASYNC_DRIVER_PREFIX, 1)


@lru_cache
def get_engine() -> AsyncEngine:
    """Return a cached `AsyncEngine` instance.

    The engine is created once per process and reused across the
    application, as recommended by SQLAlchemy for connection pooling
    efficiency.

    Returns:
        A configured `AsyncEngine` connected to the application database.

    Raises:
        RuntimeError: If the database is not configured.
    """
    settings = get_settings()
    return create_async_engine(
        _get_async_database_url(),
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return a cached `async_sessionmaker` bound to the shared engine.

    Returns:
        An `async_sessionmaker` factory that produces `AsyncSession`
        instances configured for use with FastAPI's request lifecycle.

    Raises:
        RuntimeError: If the database is not configured.
    """
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )