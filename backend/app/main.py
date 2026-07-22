"""Application entry point.

Initializes application-wide logging and registers the request logging
middleware. This module intentionally contains no business logic.
"""

from fastapi import FastAPI

from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware

def create_application() -> FastAPI:
    setup_logging()

    app = FastAPI()

    app.add_middleware(RequestLoggingMiddleware)

    return app


app = create_application()

app.add_middleware(RequestLoggingMiddleware)