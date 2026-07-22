"""Pydantic schemas for user data."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for registering a new user.

    Attributes:
        email: The user's email address. Used as the login identifier.
        password: The user's plaintext password. Never stored directly;
            it is hashed before persistence.
        full_name: Optional display name for the user.
    """

    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Plaintext password, 8-128 characters.",
    )
    full_name: str | None = Field(default=None, max_length=255)


class UserRead(BaseModel):
    """Public representation of a user, safe to return in API responses.

    Attributes:
        id: The user's unique identifier.
        email: The user's email address.
        full_name: The user's display name, if set.
        is_active: Whether the account is active.
        is_superuser: Whether the account has administrative privileges.
        created_at: Timestamp when the account was created.
        updated_at: Timestamp when the account was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime