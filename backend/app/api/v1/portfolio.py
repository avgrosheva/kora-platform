"""Portfolio API routes.

Routers stay thin: they parse the request, delegate to
`PortfolioService`, and translate domain exceptions into HTTP
responses. No aggregation or ranking logic lives here.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.config import get_settings
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.portfolio import PortfolioResponse
from app.services.portfolio_service import (
    OrganizationAccessDeniedError,
    PortfolioService,
)

settings = get_settings()

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/portfolio", tags=["portfolio"])


@router.get(
    "",
    response_model=PortfolioResponse,
    summary="Get an organization's portfolio analytics",
)
async def get_portfolio(
    organization_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioResponse:
    """Return the aggregated portfolio view for an organization.

    All rankings, averages, risk indicators, and distribution buckets
    are computed server-side and are fully deterministic — no AI calls
    are made.

    Args:
        organization_id: The organization to build the portfolio for.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The organization's portfolio.

    Raises:
        HTTPException: With status 404 if the user is not a member of
            the organization.
    """
    try:
        return await PortfolioService.get_portfolio(
            db=db, organization_id=organization_id, actor_id=current_user.id
        )
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc