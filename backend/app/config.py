"""Application configuration module.

This module defines the strongly-typed application settings, sourced from
environment variables and/or a `.env` file, using `pydantic-settings`.

The `get_settings` function is cached with `functools.lru_cache` so that
the `.env` file and environment are parsed only once per process, and the
resulting `Settings` instance is reused across the application (e.g. via
FastAPI dependency injection).

Note:
    PostgreSQL and OpenAI integrations are not yet implemented at this
    stage of the project. `POSTGRES_PASSWORD` and `OPENAI_API_KEY` are
    therefore optional, allowing the application to start without those
    services configured.
"""

import json
from functools import lru_cache
from typing import Annotated, List, Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration settings.

    Settings are loaded from environment variables, falling back to values
    defined in a `.env` file (see `.env.example` for the full list of
    supported variables). All values are validated and type-checked at
    startup, so misconfiguration fails fast instead of causing runtime
    errors deep in the application.

    Attributes:
        APP_NAME: Human-readable name of the application.
        APP_VERSION: Semantic version of the application.
        APP_ENV: Deployment environment (development, staging, production).
        DEBUG: Whether debug mode is enabled. Must be False in production.
        SECRET_KEY: Secret key used for cryptographic signing.
        JWT_ALGORITHM: Algorithm used to sign JWT tokens.
        ACCESS_TOKEN_EXPIRE_MINUTES: Lifetime of an access token, in minutes.
        POSTGRES_HOST: Hostname of the PostgreSQL server.
        POSTGRES_PORT: Port of the PostgreSQL server.
        POSTGRES_DB: Name of the PostgreSQL database.
        POSTGRES_USER: PostgreSQL username.
        POSTGRES_PASSWORD: PostgreSQL password. Optional while the
            PostgreSQL integration is not yet implemented.
        OPENAI_API_KEY: API key used to authenticate with OpenAI. Optional
            while the OpenAI integration is not yet implemented.
        OPENAI_MODEL: Default OpenAI model identifier to use.
        API_V1_PREFIX: URL prefix for version 1 of the API.
        CORS_ORIGINS: List of origins allowed to make cross-origin requests.
        LOG_LEVEL: Minimum severity level for application logging.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = Field(
        default="Kora Revenue Intelligence Platform",
        description="Human-readable name of the application.",
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Semantic version of the application.",
    )
    APP_ENV: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment.",
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode. Must be disabled in production.",
    )
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Secret key used for cryptographic signing. Required.",
    )

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm used to sign JWT tokens.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        gt=0,
        description="Lifetime of an access token, in minutes.",
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = Field(
        default="localhost",
        description="Hostname of the PostgreSQL server.",
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        gt=0,
        lt=65536,
        description="Port of the PostgreSQL server.",
    )
    POSTGRES_DB: str = Field(
        default="kora_db",
        description="Name of the PostgreSQL database.",
    )
    POSTGRES_USER: str = Field(
        default="kora_user",
        description="PostgreSQL username.",
    )
    POSTGRES_PASSWORD: str | None = Field(
        default=None,
        description=(
            "PostgreSQL password. Optional while the PostgreSQL "
            "integration is not yet implemented; the application can "
            "start without it."
        ),
    )

    # ------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str | None = Field(
        default=None,
        description=(
            "API key used to authenticate with OpenAI. Optional while "
            "the OpenAI integration is not yet implemented; the "
            "application can start without it."
        ),
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Default OpenAI model identifier to use.",
    )

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="URL prefix for version 1 of the API.",
    )
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="List of origins allowed to make cross-origin requests.",
    )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = Field(
        default="INFO",
        description="Minimum severity level for application logging.",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | List[str]) -> List[str]:
        """Parse `CORS_ORIGINS` from a comma-separated string or JSON array.

        Because `CORS_ORIGINS` is annotated with `NoDecode`,
        `pydantic-settings` skips its default JSON-decoding step for this
        field and passes the raw environment variable value straight to
        this validator. This allows `.env` files to use either format:

        - Comma-separated (recommended, no quoting needed):
          `CORS_ORIGINS=http://localhost:3000,http://localhost:8080`
        - JSON array (also supported):
          `CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]`

        Args:
            value: Raw value provided for `CORS_ORIGINS`, either a
                comma-separated string, a JSON array string, or a native
                list of strings.

        Returns:
            A list of origin strings with surrounding whitespace stripped.

        Raises:
            ValueError: If the value looks like a JSON array but is not
                valid JSON, or does not decode to a list of strings.
        """
        if isinstance(value, list):
            return value

        stripped = value.strip()

        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "CORS_ORIGINS looks like a JSON array but is not valid JSON."
                ) from exc
            if not isinstance(parsed, list) or not all(
                isinstance(item, str) for item in parsed
            ):
                raise ValueError("CORS_ORIGINS JSON array must contain only strings.")
            return [origin.strip() for origin in parsed if origin.strip()]

        return [origin.strip() for origin in stripped.split(",") if origin.strip()]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key_not_default(cls, value: str) -> str:
        """Reject obviously unsafe placeholder secret keys.

        Args:
            value: The provided `SECRET_KEY` value.

        Returns:
            The validated `SECRET_KEY` value.

        Raises:
            ValueError: If the secret key is a known-insecure placeholder.
        """
        insecure_values = {
            "changeme",
            "secret",
            "password",
            "your-secret-key",
            "generate_a_real_secret_here",
        }
        if value.strip().lower() in insecure_values:
            raise ValueError(
                "SECRET_KEY must not be a placeholder value. "
                "Generate a strong secret, e.g. via `openssl rand -hex 32`."
            )
        return value

    @field_validator("POSTGRES_PASSWORD")
    @classmethod
    def validate_postgres_password_not_placeholder(
        cls, value: str | None
    ) -> str | None:
        """Reject placeholder values for `POSTGRES_PASSWORD` when provided.

        Since PostgreSQL is not yet integrated, `POSTGRES_PASSWORD` is
        optional. Validation is only performed when a value is actually
        provided; `None` is passed through unchanged.

        Args:
            value: The provided `POSTGRES_PASSWORD` value, or `None`.

        Returns:
            The validated `POSTGRES_PASSWORD` value, or `None`.

        Raises:
            ValueError: If a non-`None` value is an empty/blank string.
        """
        if value is None:
            return None
        if not value.strip():
            raise ValueError("POSTGRES_PASSWORD must not be an empty string.")
        return value

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_api_key_not_placeholder(
        cls, value: str | None
    ) -> str | None:
        """Reject the placeholder value for `OPENAI_API_KEY` when provided.

        Since OpenAI is not yet integrated, `OPENAI_API_KEY` is optional.
        Validation is only performed when a value is actually provided;
        `None` is passed through unchanged.

        Args:
            value: The provided `OPENAI_API_KEY` value, or `None`.

        Returns:
            The validated `OPENAI_API_KEY` value, or `None`.

        Raises:
            ValueError: If the value is the known placeholder used in
                `.env.example`.
        """
        if value is None:
            return None
        if value.strip().lower() == "your_openai_api_key_here":
            raise ValueError(
                "OPENAI_API_KEY must not be a placeholder value. "
                "Provide a real OpenAI API key in your .env file."
            )
        return value

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL(self) -> str | None:
        """Build the PostgreSQL connection URL from individual components.

        Returns:
            A fully-formed PostgreSQL DSN in the form
            `postgresql+psycopg://user:password@host:port/db`, or `None`
            if `POSTGRES_PASSWORD` is not set, since the PostgreSQL
            integration is not yet implemented.
        """
        if not self.POSTGRES_PASSWORD:
            return None
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        """Indicate whether the application is running in production.

        Returns:
            True if `APP_ENV` is `"production"`, otherwise False.
        """
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached, singleton `Settings` instance.

    Using `functools.lru_cache` ensures the `.env` file and environment
    variables are parsed only once per process. FastAPI can depend on this
    function (e.g. `Depends(get_settings)`) to inject configuration
    without re-reading the environment on every request.

    Returns:
        The cached application `Settings` instance.
    """
    return Settings()