"""Semantic retrieval over indexed document chunks.

Performs organization-scoped cosine-similarity search over
`DocumentEmbedding` rows using pgvector. This is a pure retrieval
layer — it returns matching chunks only; no answer generation or
summarization happens here (that is explicitly out of scope for this
milestone, reserved for a future chat layer). Services operate directly
on `AsyncSession` — there is no repository layer in this project's
architecture.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_embedding import DocumentEmbedding
from app.models.organization import Membership
from app.schemas.rag import SearchResultRead
from app.services.embedding_service import EmbeddingProvider, EmbeddingService


class RetrievalServiceError(Exception):
    """Base exception for semantic retrieval failures."""


class OrganizationAccessDeniedError(RetrievalServiceError):
    """Raised when the actor is not a member of the target organization.

    Raised identically whether the organization does not exist or the
    actor simply isn't a member of it. Defined locally, consistent with
    this project's existing pattern of each service owning its own copy
    of this exception.
    """


async def _require_membership(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Assert that a user is a member of an organization.

    Args:
        db: The active database session.
        organization_id: The organization's id.
        user_id: The user's id.

    Raises:
        OrganizationAccessDeniedError: If no membership exists.
    """
    result = await db.execute(
        select(Membership.id).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise OrganizationAccessDeniedError("Organization not found.")


class RetrievalService:
    """Semantic search over an organization's indexed document chunks."""

    @staticmethod
    async def semantic_search(
        db: AsyncSession,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        query: str,
        top_k: int,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> list[SearchResultRead]:
        """Find the chunks most semantically similar to a query.

        Args:
            db: The active database session.
            organization_id: The organization to search within.
            actor_id: The id of the requesting user.
            query: The search query text.
            top_k: The maximum number of results to return.
            embedding_provider: The embedding provider to use for the
                query. Defaults to `OpenAIEmbeddingProvider`. Injectable
                for testing.

        Returns:
            The most similar chunks, ordered by cosine similarity
            (highest first). Returns an empty list if `query` is blank,
            or if no indexed chunks exist for the organization.

        Raises:
            OrganizationAccessDeniedError: If the actor is not a member
                of the organization.
            EmbeddingServiceNotConfiguredError: If no OpenAI API key is
                configured, or it is rejected as invalid (propagated
                from `EmbeddingService`).
            EmbeddingRequestFailedError: If the query's embedding
                request fails after retrying once (propagated from
                `EmbeddingService`).
            InvalidEmbeddingDimensionError: If the query's embedding has
                the wrong dimensionality (propagated from
                `EmbeddingService`).
        """
        await _require_membership(db, organization_id, actor_id)

        if not query.strip():
            return []

        query_vectors = await EmbeddingService.embed_texts(
            [query], provider=embedding_provider
        )
        query_vector = query_vectors[0]

        distance = DocumentEmbedding.embedding.cosine_distance(query_vector).label(
            "distance"
        )

        stmt = (
            select(
                DocumentEmbedding.document_id,
                DocumentEmbedding.chunk_index,
                DocumentEmbedding.text,
                distance,
            )
            .join(Document, Document.id == DocumentEmbedding.document_id)
            .where(Document.organization_id == organization_id)
            .order_by(distance.asc())
            .limit(top_k)
        )

        rows = (await db.execute(stmt)).all()

        return [
            SearchResultRead(
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                text=row.text,
                similarity_score=round(1.0 - row.distance, 4),
            )
            for row in rows
        ]