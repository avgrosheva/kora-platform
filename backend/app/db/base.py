"""Declarative base for all SQLAlchemy ORM models.

This module defines the shared `Base` class that all database models in
the application must inherit from. It contains no models itself; model
definitions live in `app/models/`.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# A consistent naming convention ensures Alembic autogenerate produces
# deterministic, predictable constraint and index names across
# environments, instead of relying on database-specific defaults.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models.

    All SQLAlchemy models in the application should inherit from this
    class so they share a single `MetaData` instance (with a consistent
    naming convention), which Alembic relies on for autogeneration and
    for producing stable constraint names.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)