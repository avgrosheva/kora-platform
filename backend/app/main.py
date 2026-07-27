"""Application entry point.

Initializes logging, validates configuration, registers middleware
(request logging, CORS, GZip), global exception handlers, health
endpoints, and all API routers. No business logic lives here.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.portfolio import router as portfolio_router
from app.api.v1.search import router as search_router
from app.config import validate_settings_or_exit
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestLoggingMiddleware

# Fail fast: validate configuration before anything else initializes.
settings = validate_settings_or_exit()

setup_logging()
logger = get_logger(__name__)
logger.info(
    "Starting application",
    extra={"app_env": settings.APP_ENV, "app_version": settings.APP_VERSION},
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Kora Technologies Revenue Intelligence Platform API. Provides "
        "authentication, organization management, document ingestion and "
        "AI-driven analysis, financial metrics extraction, investment "
        "scoring, portfolio analytics, retrieval-augmented chat, and "
        "due diligence report generation."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Registration, login, and current-user identity."},
        {"name": "organizations", "description": "Organizations, memberships, roles, and invitations."},
        {"name": "documents", "description": "Document upload, processing, AI analysis, financial extraction, scoring, indexing, and report export."},
        {"name": "dashboard", "description": "Per-organization aggregate statistics."},
        {"name": "portfolio", "description": "Portfolio-wide analytics across all analyzed companies in an organization."},
        {"name": "search", "description": "Semantic search over indexed document chunks."},
        {"name": "chat", "description": "Single-turn retrieval-augmented chat over indexed documents."},
        {"name": "health", "description": "Liveness and readiness probes for orchestrators."},
    ],
)

register_exception_handlers(app)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(documents_router)
app.include_router(dashboard_router)
app.include_router(portfolio_router)
app.include_router(search_router)
app.include_router(chat_router)