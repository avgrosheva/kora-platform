"""Declarative base for all SQLAlchemy ORM models.

This module defines the shared `Base` class that all database models in
the application must inherit from. It contains no models itself; model
definitions live in `app/db/models/`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models.

    All SQLAlchemy models in the application should inherit from this
    class so they share a single `MetaData` instance, which is required
    for features such as Alembic autogeneration and consistent table
    registration.
    """