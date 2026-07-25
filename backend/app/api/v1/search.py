"""Semantic search API routes.

Routers stay thin: they parse the request, delegate to
`RetrievalService`, and translate domain exceptions into HTTP
responses. No retrieval or ranking logic lives here.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.config import get_settings
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.rag import SearchResponse
from app.services.embedding_service import (
    EmbeddingRequestFailedError,
    EmbeddingServiceNotConfiguredError,
    InvalidEmbeddingDimensionError,
)
from app.services.retrieval_service import (
    OrganizationAccessDeniedError,
    RetrievalService,
)

settings = get_settings()

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/search", tags=["search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Semantic search over an organization's indexed documents",
)
async def search(
    organization_id: uuid.UUID = Query(...),
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SearchResponse:
    """Return the chunks most semantically similar to a query.

    This is retrieval only — no answer is generated or summarized from
    the results. That is explicitly out of scope for this milestone.

    Args:
        organization_id: The organization to search within.
        query: The search query text.
        top_k: The maximum number of results to return (1-50).
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The matching chunks, ordered by similarity.

    Raises:
        HTTPException: With status 404 if the user is not a member of
            the organization; 503 if the embedding service is not
            configured; 502 if the query's embedding request fails or
            returns an invalid response.
    """
    try:
        results = await RetrievalService.semantic_search(
            db=db,
            organization_id=organization_id,
            actor_id=current_user.id,
            query=query,
            top_k=top_k,
        )
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except EmbeddingServiceNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (EmbeddingRequestFailedError, InvalidEmbeddingDimensionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return SearchResponse(
        query=query, top_k=top_k, results=results, total=len(results)
    )