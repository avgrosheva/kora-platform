"""Database models package.

Importing this package ensures all ORM models are registered on
`Base.metadata`, which is required for Alembic autogeneration to detect
them.
"""

from app.models.user import User

__all__ = ["User"]