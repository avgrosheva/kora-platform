"""Dashboard API routes.

Routers stay thin: they parse the request, delegate to
`DashboardService`, and translate domain exceptions into HTTP
responses. No aggregation or computation logic lives here.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.config import get_settings
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import (
    DashboardService,
    OrganizationAccessDeniedError,
)

settings = get_settings()

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get an organization's dashboard",
)
async def get_dashboard(
    organization_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardResponse:
    """Return the aggregated dashboard for an organization.

    All counts, averages, rankings, and thresholds are computed
    server-side; the response requires no further calculation by the
    frontend.

    Args:
        organization_id: The organization to build the dashboard for.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The organization's dashboard.

    Raises:
        HTTPException: With status 404 if the user is not a member of
            the organization.
    """
    try:
        return await DashboardService.get_dashboard(
            db=db, organization_id=organization_id, actor_id=current_user.id
        )
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc