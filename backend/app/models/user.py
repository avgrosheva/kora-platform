"""SQLAlchemy ORM model for application users."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    """Represents an application user account.

    Attributes:
        id: Primary key, a randomly generated UUID.
        email: Unique, indexed email address used as the login
            identifier.
        hashed_password: Hash of the user's password. The raw password
            is never stored.
        full_name: Optional display name for the user.
        is_active: Whether the account is active. Inactive accounts
            must not be able to authenticate.
        is_superuser: Whether the account has elevated administrative
            privileges.
        created_at: Timezone-aware timestamp when the record was
            created.
        updated_at: Timezone-aware timestamp when the record was last
            updated.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the user.

        Returns:
            A string identifying the user by id and email, safe to
            include in logs (contains no password data).
        """
        return f"<User id={self.id} email={self.email!r}>"