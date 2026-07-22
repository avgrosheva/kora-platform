"""Security primitives: password hashing and JWT access tokens.

This module provides the low-level cryptographic building blocks used by
the authentication feature: password hashing/verification via
`pwdlib`, and access-token creation/decoding via `PyJWT`. It contains no
routes, schemas, or services — only reusable, framework-adjacent
security utilities and the shared `oauth2_scheme` dependency.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, ValidationError

from app.config import get_settings

settings = get_settings()

_password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
)

_TOKEN_TYPE_ACCESS = "access"


class TokenPayload(BaseModel):
    """Decoded contents of a JWT access token.

    Attributes:
        sub: The token subject, typically the user's id as a string.
        exp: Expiration time of the token, as a UTC datetime.
        iat: Time the token was issued, as a UTC datetime.
        type: The token type. Always `"access"` for this module, since
            refresh tokens are not implemented.
    """

    sub: str
    exp: datetime
    iat: datetime
    type: str


class TokenError(Exception):
    """Base exception for token creation or validation failures."""


class TokenExpiredError(TokenError):
    """Raised when a JWT access token has expired."""


class InvalidTokenError(TokenError):
    """Raised when a JWT access token is malformed, tampered with, or
    otherwise fails validation."""


def hash_password(password: str) -> str:
    """Hash a plaintext password.

    Args:
        password: The plaintext password to hash.

    Returns:
        The resulting password hash, safe to store in the database.
    """
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Args:
        password: The plaintext password supplied by the user.
        hashed_password: The previously hashed password to compare
            against.

    Returns:
        True if the password matches the hash, False otherwise. Returns
        False (rather than raising) for malformed or unrecognized hash
        values, so callers can treat any verification failure uniformly.
    """
    try:
        return _password_hash.verify(password, hashed_password)
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject, typically the authenticated user's
            id as a string.

    Returns:
        An encoded JWT access token, signed with `Settings.SECRET_KEY`
        using `Settings.JWT_ALGORITHM`, valid for
        `Settings.ACCESS_TOKEN_EXPIRE_MINUTES` minutes.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
        "type": _TOKEN_TYPE_ACCESS,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT access token.

    Verifies the token's signature and expiration, and confirms it is
    an access token (not some other token type).

    Args:
        token: The encoded JWT access token to decode.

    Returns:
        The validated token payload.

    Raises:
        TokenExpiredError: If the token has expired.
        InvalidTokenError: If the token's signature is invalid, it is
            malformed, it is missing required claims, or it is not an
            access token.
    """
    try:
        raw_payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Access token is invalid.") from exc

    try:
        payload = TokenPayload(**raw_payload)
    except ValidationError as exc:
        raise InvalidTokenError("Access token payload is malformed.") from exc

    if payload.type != _TOKEN_TYPE_ACCESS:
        raise InvalidTokenError("Token is not a valid access token.")

    return payload


def get_token_payload(token: str) -> TokenPayload:
    """Decode a JWT access token, raising an HTTP-friendly error on failure.

    Intended for use as (or within) a FastAPI dependency, where token
    errors should surface to the client as a 401 response rather than
    propagate as raw domain exceptions.

    Args:
        token: The encoded JWT access token to decode, typically
            obtained via `oauth2_scheme`.

    Returns:
        The validated token payload.

    Raises:
        HTTPException: With status 401 if the token is expired, invalid,
            or malformed.
    """
    try:
        return decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc