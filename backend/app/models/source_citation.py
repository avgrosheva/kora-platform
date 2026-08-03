"""SQLAlchemy ORM model for source provenance of extracted facts.

Every important extracted value — a company-overview field, a financial
fact, a competitor, a risk, etc. — should be traceable back to the exact
passage in the source document it came from. This model is that
provenance record. It is deliberately generic (`field_path` is a string
key) rather than one FK column per possible field, so a single table
covers scalar fields (`"analysis.industry"`), array items
(`"analysis.competitors[2]"`), and financial facts
(`FinancialFact.source_citation_id`) without a combinatorial explosion
of per-entity citation tables.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.document_embedding import DocumentEmbedding


class SourceCitation(Base):
    """Provenance for a single extracted fact, linking it back to its source.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The document this citation belongs to.
        field_path: A string key identifying which extracted field this
            citation supports (e.g. `"analysis.company_name"`,
            `"analysis.competitors[1]"`, or a `FinancialFact.id`
            reference for financial facts). Not a foreign key by
            design — the referenced structure varies (JSONB field on
            `DocumentAnalysis`, or a `FinancialFact` row), so this is
            an application-level key rather than a database-enforced
            relationship.
        page_number: The page in the source document the quote appears
            on, or `None` if the document has no page concept (e.g.
            a `.txt` file) or the page could not be determined (e.g.
            documents indexed before page tracking was added).
        chunk_id: The `DocumentEmbedding` chunk the quote was found in,
            if the citation was resolved via retrieval rather than
            supplied directly by the extraction prompt.
        quote: The exact supporting passage from the source document.
            Never paraphrased — this must be the literal text, so the
            frontend can display or highlight it faithfully.
        confidence: The extraction's confidence in this specific
            citation (0.0-1.0), independent of the overall document's
            coverage/confidence assessment.
        extraction_version: A version tag for the extraction logic that
            produced this citation (e.g. a prompt version string),
            preserved for auditability per the project's versioning
            requirements.
        created_at: Timezone-aware timestamp when this citation was
            recorded.
        document: The related `Document`.
        chunk: The related `DocumentEmbedding`, if linked.
    """

    __tablename__ = "source_citations"

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
    field_path: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_embeddings.id", ondelete="SET NULL"),
        nullable=True,
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="citations")
    chunk: Mapped["DocumentEmbedding | None"] = relationship()

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the citation.

        Returns:
            A string identifying the citation by document id and field
            path (never includes the quote, to keep logs concise).
        """
        return (
            f"<SourceCitation document_id={self.document_id} "
            f"field_path={self.field_path!r}>"
        )