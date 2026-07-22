"""Application entry point.

Initializes application-wide logging, registers the request logging
middleware, and includes the API routers.
"""

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware

setup_logging()

app = FastAPI()

app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)