"""Application entry point.

Initializes application-wide logging, registers the request logging
middleware, and includes the API routers.
"""

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.documents import router as documents_router
from app.api.v1.organizations import router as organizations_router
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware

setup_logging()

app = FastAPI()

app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(documents_router)
app.include_router(dashboard_router)