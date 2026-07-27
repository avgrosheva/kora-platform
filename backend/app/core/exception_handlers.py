"""Global exception handlers.

Ensures every unhandled exception produces a consistent JSON error
envelope and is logged with its request ID, instead of leaking a raw
traceback (in production) or an inconsistent shape to API consumers.
Domain-specific exceptions continue to be translated to precise status
codes inside each router, as established throughout the project; these
handlers are the last-resort safety net for anything that isn't.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _request_id(request: Request) -> str:
    """Fetch the request ID attached by `RequestLoggingMiddleware`.

    Args:
        request: The incoming request.

    Returns:
        The request's UUID4 id, or `"-"` if unavailable (e.g. the
        middleware itself failed to run).
    """
    return getattr(request.state, "request_id", "-")


def _error_response(
    request: Request, status_code: int, message: str, error_type: str
) -> JSONResponse:
    """Build the standard error envelope.

    Args:
        request: The incoming request.
        status_code: The HTTP status code to return.
        message: A human-readable error message.
        error_type: A short, stable machine-readable error category.

    Returns:
        A `JSONResponse` with a consistent shape:
        `{"detail": ..., "error_type": ..., "request_id": ...}`.
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message,
            "error_type": error_type,
            "request_id": _request_id(request),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Preserve FastAPI's normal HTTPException shape plus request_id."""
        return _error_response(
            request, exc.status_code, str(exc.detail), "http_error"
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return a consistent envelope for request validation failures."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "error_type": "validation_error",
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all for any exception not otherwise handled.

        Logs the full traceback with the request's id, and returns a
        generic message in production (never leaking internals), or the
        exception's string representation in development for faster
        debugging.
        """
        logger.exception(
            "Unhandled exception reached global handler",
            extra={"request_id": _request_id(request)},
        )

        message = (
            str(exc)
            if settings.APP_ENV == "development"
            else "An unexpected error occurred. Please try again later."
        )
        return _error_response(
            request, status.HTTP_500_INTERNAL_SERVER_ERROR, message, "internal_error"
        )