"""FastAPI dependencies for database access.

Provides the `get_db` dependency, which yields a request-scoped
`AsyncSession` for use in route handlers and other dependencies via
FastAPI's dependency injection system.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped `AsyncSession`.

    Intended for use with FastAPI's `Depends`. The session is closed
    automatically once the request has been handled, regardless of
    whether it completed successfully or raised an exception.

    Yields:
        An `AsyncSession` bound to the application's database engine.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session