"""Pydantic schemas for authentication requests and responses."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials submitted to authenticate a user.

    Attributes:
        email: The user's email address.
        password: The user's plaintext password.
    """

    email: EmailStr
    password: str = Field(min_length=1, description="Plaintext password.")


class TokenResponse(BaseModel):
    """Response returned after a successful login.

    Attributes:
        access_token: The signed JWT access token.
        token_type: The token type, always `"bearer"`.
    """

    access_token: str
    token_type: str = "bearer"