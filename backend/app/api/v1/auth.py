"""Authentication API routes: register, login, and current-user lookup."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import oauth2_scheme
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import (
    AuthService,
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    UserNotFoundError,
)

settings = get_settings()

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])


async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve and return the currently authenticated, active user.

    Intended for use with `Depends` on any route that requires
    authentication.

    Args:
        token: The bearer token extracted from the `Authorization`
            header by `oauth2_scheme`.
        db: The request-scoped database session.

    Returns:
        The authenticated, active `User`.

    Raises:
        HTTPException: With status 401 if the token does not resolve to
            an existing user, or 403 if the user account is inactive.
    """
    try:
        return await AuthService.get_current_user(db=db, token=token)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Register a new user account.

    Args:
        payload: The registration details (email, password, full name).
        db: The request-scoped database session.

    Returns:
        The newly created user.

    Raises:
        HTTPException: With status 409 if the email is already
            registered.
    """
    try:
        return await AuthService.register(
            db=db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain an access token",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and issue an access token.

    Args:
        payload: The login credentials (email, password).
        db: The request-scoped database session.

    Returns:
        A `TokenResponse` containing the signed JWT access token.

    Raises:
        HTTPException: With status 401 if the credentials are invalid,
            or 403 if the account has been deactivated.
    """
    try:
        access_token = await AuthService.authenticate(
            db=db,
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return TokenResponse(access_token=access_token)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the currently authenticated user",
)
async def read_current_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Return the profile of the currently authenticated user.

    Args:
        current_user: The authenticated user, resolved from the bearer
            token by `get_current_active_user`.

    Returns:
        The current user's profile.
    """
    return current_user