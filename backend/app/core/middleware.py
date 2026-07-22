"""HTTP middleware for request logging and request correlation IDs.

Provides a single ASGI middleware that assigns a unique request ID to
every incoming HTTP request, logs the request lifecycle (start,
completion, duration), and logs unhandled exceptions before they
propagate further up the stack.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)

_REQUEST_ID_HEADER = "X-Request-ID"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs the full request/response lifecycle.

    For every incoming request, this middleware:

    - Generates a UUID4 request ID and attaches it to `request.state`.
    - Logs the incoming request's method and path.
    - Logs the completed request's status code and duration in
      milliseconds.
    - Logs unhandled exceptions raised while processing the request,
      then re-raises them so FastAPI's own exception handling is
      unaffected.
    - Echoes the request ID back to the client via the `X-Request-ID`
      response header.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process a request, logging its lifecycle and timing.

        Args:
            request: The incoming HTTP request.
            call_next: Callable that forwards the request to the next
                middleware or route handler in the stack.

        Returns:
            The HTTP response, with the `X-Request-ID` header attached.

        Raises:
            Exception: Re-raises any unhandled exception after logging
                it, leaving upstream error handling behavior unchanged.
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()

        logger.info(
            "Incoming request: %s %s",
            request.method,
            request.url.path,
            extra={"request_id": request_id},
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Unhandled exception for %s %s after %.2fms",
                request.method,
                request.url.path,
                duration_ms,
                extra={"request_id": request_id},
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Completed request: %s %s status=%d duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )

        response.headers[_REQUEST_ID_HEADER] = request_id
        return response