"""SQLAlchemy ORM model for document text-chunk embeddings."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.rag_config import EMBEDDING_DIMENSIONS
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentEmbedding(Base):
    """A single chunk of a document's text, with its vector embedding.

    A document has many embeddings (one per chunk). Reindexing a
    document replaces all of its existing chunks/embeddings rather than
    appending to them, so there is no historical versioning here — only
    the current index state.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The document this chunk belongs to.
        chunk_index: The chunk's position within the document, starting
            at 0. Used to reconstruct chunk ordering and to identify
            which part of the source text a search result came from.
        text: The chunk's raw text content.
        embedding: The chunk's vector embedding, produced by
            `EmbeddingService`. Fixed at `EMBEDDING_DIMENSIONS` (1536)
            dimensions, matching OpenAI's `text-embedding-3-small`.
        created_at: Timezone-aware timestamp when this chunk/embedding
            was created.
        document: The related `Document`.

        page_number: The page number (1-indexed) in the source document
            this chunk's text came from, or `None` if the document has
            no page concept (e.g. `.txt`), or if this chunk was created
            before page tracking was added (pre-migration documents).
    """

    __tablename__ = "document_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="embeddings")

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the chunk.

        Returns:
            A string identifying the chunk by document id and index.
        """
        return (
            f"<DocumentEmbedding document_id={self.document_id} "
            f"chunk_index={self.chunk_index}>"
        )