"""SQLAlchemy ORM model for AI-generated document analyses."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentAnalysis(Base):
    """Structured business information extracted from a document by AI.

    Each document has at most one analysis. Re-running analysis updates
    the existing row rather than creating a new one.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The analyzed document. Unique, so each document
            has at most one analysis.
        summary: A brief natural-language summary of the document.
        company_name: The name of the company described in the
            document, or `None` if not identifiable.
        industry: The company's industry, or `None` if not identifiable.
        business_model: A description of the company's business model,
            or `None` if not identifiable.
        key_products: The company's key products or services, or `None`
            if not identifiable.
        risks: The main risks facing the company, or `None` if not
            identifiable. Corresponds to `main_risks` in the AI's
            output schema.
        opportunities: Growth opportunities identified for the company,
            or `None` if not identifiable. Corresponds to
            `growth_opportunities` in the AI's output schema.
        revenue_streams: The company's revenue streams, or `None` if
            not identifiable.
        customers: The company's target customers, or `None` if not
            identifiable. Corresponds to `target_customers` in the AI's
            output schema.
        competitors: The company's competitors, or `None` if not
            identifiable.
        raw_json: The complete, validated AI response, stored verbatim.
            Kept so future features (embeddings, RAG) can be built on
            top of the full analysis without requiring an API or schema
            change.
        created_at: Timezone-aware timestamp when the analysis was
            first created. Not updated on re-analysis, since there is
            no `updated_at` in this model; re-analysis overwrites the
            structured fields but the row's identity and original
            creation time are preserved.
        document: The related `Document`.
    """

    __tablename__ = "document_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_products: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    risks: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    opportunities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    revenue_streams: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    customers: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    competitors: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="analysis")

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the analysis.

        Returns:
            A string identifying the analysis by document id.
        """
        return f"<DocumentAnalysis document_id={self.document_id}>"