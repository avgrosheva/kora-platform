"""Document indexing orchestration for RAG retrieval.

Reads a processed document's text, splits it into chunks, generates
embeddings for each chunk, and persists them — replacing any prior
index state for that document. Services operate directly on
`AsyncSession` — there is no repository layer in this project's
architecture.
"""

import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentStatus
from app.models.document_embedding import DocumentEmbedding
from app.services.chunking_service import ChunkingService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingProvider, EmbeddingService


class DocumentIndexServiceError(Exception):
    """Base exception for document indexing failures."""


class DocumentNotProcessedError(DocumentIndexServiceError):
    """Raised when indexing is requested for a document whose text
    extraction has not completed successfully."""


class NoIndexableContentError(DocumentIndexServiceError):
    """Raised when a document's text produces no non-empty chunks to
    index (e.g. the document is effectively empty)."""


class DocumentIndexService:
    """Indexes (and reindexes) documents for semantic retrieval."""

    @staticmethod
    async def index_document(
        db: AsyncSession,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
        chunking_service: ChunkingService | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> int:
        """Chunk, embed, and index a document, replacing any prior index.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the user requesting indexing.
            chunking_service: The chunking configuration to use.
                Defaults to `ChunkingService()` with its default chunk
                size/overlap. Injectable for testing and future tuning.
            embedding_provider: The embedding provider to use. Defaults
                to `OpenAIEmbeddingProvider`. Injectable for testing and
                future provider swaps.

        Returns:
            The number of chunks indexed.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization
                (propagated from `DocumentService.get_document`).
            DocumentNotProcessedError: If the document's text extraction
                has not completed successfully (`status != COMPLETED`).
            NoIndexableContentError: If the document's text produces no
                non-empty chunks.
            EmbeddingServiceNotConfiguredError: If no OpenAI API key is
                configured, or it is rejected as invalid (propagated
                from `EmbeddingService`).
            EmbeddingRequestFailedError: If the embeddings request fails
                after retrying once (propagated from `EmbeddingService`).
            InvalidEmbeddingDimensionError: If a returned embedding has
                the wrong dimensionality (propagated from
                `EmbeddingService`).
        """
        document = await DocumentService.get_document(db, document_id, actor_id)

        if document.status != DocumentStatus.COMPLETED:
            raise DocumentNotProcessedError(
                "Document must be fully processed (status=completed) "
                "before it can be indexed."
            )

        chunker = chunking_service or ChunkingService()
        chunks = chunker.chunk(document.text_content or "")

        if not chunks:
            raise NoIndexableContentError(
                "Document text produced no indexable content."
            )

        vectors = await EmbeddingService.embed_texts(
            [chunk.text for chunk in chunks], provider=embedding_provider
        )

        await db.execute(
            delete(DocumentEmbedding).where(
                DocumentEmbedding.document_id == document_id
            )
        )

        db.add_all(
            [
                DocumentEmbedding(
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    embedding=vector,
                )
                for chunk, vector in zip(chunks, vectors)
            ]
        )

        await db.commit()
        return len(chunks)