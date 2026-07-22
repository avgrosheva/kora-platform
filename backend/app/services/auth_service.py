"""Authentication business logic.

Implements user registration, credential authentication, and current-user
resolution. Services operate directly on `AsyncSession` — there is no
repository layer in this project's architecture.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    get_token_payload,
    hash_password,
    verify_password,
)
from app.models.user import User


class AuthServiceError(Exception):
    """Base exception for authentication service failures."""


class EmailAlreadyExistsError(AuthServiceError):
    """Raised when registering an email address that is already in use."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when login credentials do not match any active account."""


class InactiveUserError(AuthServiceError):
    """Raised when an operation is attempted against an inactive account."""


class UserNotFoundError(AuthServiceError):
    """Raised when a token references a user that cannot be found."""


class AuthService:
    """Authentication use cases: registration, login, current-user lookup.

    All methods are stateless and take an `AsyncSession` explicitly,
    rather than holding a session as instance state, so the service has
    no lifecycle of its own beyond the request it is used within.
    """

    @staticmethod
    async def register(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str | None,
    ) -> User:
        """Register a new user account.

        Args:
            db: The active database session.
            email: The new user's email address.
            password: The new user's plaintext password.
            full_name: The new user's optional display name.

        Returns:
            The newly created, persisted `User`.

        Raises:
            EmailAlreadyExistsError: If an account with this email
                already exists.
        """
        normalized_email = email.strip().lower()

        result = await db.execute(select(User).where(User.email == normalized_email))
        if result.scalar_one_or_none() is not None:
            raise EmailAlreadyExistsError(
                "An account with this email already exists."
            )

        user = User(
            email=normalized_email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> str:
        """Authenticate a user by email and password.

        Args:
            db: The active database session.
            email: The email address to authenticate.
            password: The plaintext password to verify.

        Returns:
            A signed JWT access token for the authenticated user.

        Raises:
            InvalidCredentialsError: If no active account matches the
                given email and password. Raised identically whether
                the email does not exist or the password is wrong, to
                avoid leaking which case occurred.
            InactiveUserError: If the account exists and the password
                is correct, but the account has been deactivated.
        """
        normalized_email = email.strip().lower()

        result = await db.execute(select(User).where(User.email == normalized_email))
        user = result.scalar_one_or_none()

        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect email or password.")

        if not user.is_active:
            raise InactiveUserError("This account has been deactivated.")

        return create_access_token(subject=str(user.id))

    @staticmethod
    async def get_current_user(db: AsyncSession, token: str) -> User:
        """Resolve the current user from a JWT access token.

        Args:
            db: The active database session.
            token: The encoded JWT access token.

        Returns:
            The authenticated, active `User`.

        Raises:
            UserNotFoundError: If the token's subject is not a valid
                user id, or does not match any existing user.
            InactiveUserError: If the user exists but has been
                deactivated.

        Note:
            Malformed, expired, or otherwise invalid tokens are rejected
            by `app.core.security.get_token_payload` itself, which raises
            an `HTTPException` before this method is reached.
        """
        payload = get_token_payload(token)

        try:
            user_id = uuid.UUID(payload.sub)
        except ValueError as exc:
            raise UserNotFoundError(
                "Token subject is not a valid user identifier."
            ) from exc

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise UserNotFoundError("User for this token no longer exists.")

        if not user.is_active:
            raise InactiveUserError("This account has been deactivated.")

        return user