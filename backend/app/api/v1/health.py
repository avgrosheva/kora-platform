"""Liveness and readiness probes.

Unauthenticated, dependency-light endpoints intended for orchestrators
(Docker healthcheck, Kubernetes probes, load balancers) — not for
application clients.
"""

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.dependencies import get_db

router = APIRouter(tags=["health"])


@router.get(
    "/liveness",
    summary="Liveness probe",
    description=(
        "Returns 200 if the application process is running and able to "
        "handle requests at all. Does not check dependencies (database, "
        "external APIs) — use /readiness for that. Intended for "
        "orchestrator restart decisions."
    ),
)
async def liveness() -> dict:
    """Report that the process is alive.

    Returns:
        A minimal status payload.
    """
    return {"status": "alive"}


@router.get(
    "/readiness",
    summary="Readiness probe",
    description=(
        "Returns 200 only if the application can serve real traffic — "
        "currently, this means the database is reachable. Returns 503 "
        "otherwise. Intended for orchestrator traffic-routing decisions "
        "(e.g. removing a pod from a load balancer)."
    ),
)
async def readiness(db: AsyncSession = Depends(get_db), response: Response = None) -> dict:
    """Report whether the application is ready to serve traffic.

    Args:
        db: The request-scoped database session.
        response: The outgoing response, used to set the status code on
            failure.

    Returns:
        A status payload indicating readiness and the database's
        reachability.
    """
    try:
        await db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False

    if not database_ok and response is not None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if database_ok else "not_ready",
        "database": "ok" if database_ok else "unreachable",
    }