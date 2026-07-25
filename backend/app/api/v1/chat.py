"""AI chat API routes.

Routers stay thin: they parse the request, delegate to `ChatService`,
and translate domain exceptions into HTTP responses. No retrieval,
prompt-construction, or generation logic lives here.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.config import get_settings
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import AIRequestFailedError, AIServiceNotConfiguredError
from app.services.chat_service import ChatService
from app.services.embedding_service import (
    EmbeddingRequestFailedError,
    EmbeddingServiceNotConfiguredError,
    InvalidEmbeddingDimensionError,
)
from app.services.retrieval_service import OrganizationAccessDeniedError

settings = get_settings()

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question over an organization's indexed documents",
)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatResponse:
    """Answer a question using retrieval-augmented generation.

    This is single-turn only: no conversation memory or chat history is
    stored or considered. Each request is answered independently, using
    only the context retrieved for that specific question.

    Args:
        payload: The organization to search, the question, and the
            number of chunks to retrieve as context.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The generated answer, its supporting sources, and the model
        used.

    Raises:
        HTTPException: With status 404 if the user is not a member of
            the organization; 503 if the embedding or chat completion
            service is not configured; 502 if the embedding or chat
            completion request fails or returns an invalid response.
    """
    try:
        return await ChatService.answer_question(
            db=db,
            organization_id=payload.organization_id,
            actor_id=current_user.id,
            question=payload.question,
            top_k=payload.top_k,
        )
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (AIServiceNotConfiguredError, EmbeddingServiceNotConfiguredError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (
        AIRequestFailedError,
        EmbeddingRequestFailedError,
        InvalidEmbeddingDimensionError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc