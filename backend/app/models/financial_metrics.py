"""SQLAlchemy ORM model for AI-derived financial KPIs."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class FinancialMetrics(Base):
    """Structured financial KPIs derived from a document's AI analysis.

    Each document has at most one financial metrics record. Re-running
    financial analysis updates the existing row rather than creating a
    new one, mirroring `DocumentAnalysis`.

    All monetary fields share a single `currency` (e.g. `"USD"`); no
    per-field currency conversion is performed. Values are stored as
    plain floats (rather than `Decimal`) so dashboard endpoints can
    consume this record directly as JSON with no additional
    transformation — see the module-level note in
    `financial_analysis_service.py` for the rationale.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The analyzed document. Unique, so each document
            has at most one financial metrics record.
        currency: The ISO 4217 currency code the figures are
            denominated in (e.g. `"USD"`), or `None` if not stated.
        revenue: Total revenue, or `None` if not identifiable.
        arr: Annual recurring revenue, or `None`. Derived from `mrr` if
            the AI provided `mrr` but not `arr`.
        mrr: Monthly recurring revenue, or `None`. Derived from `arr` if
            the AI provided `arr` but not `mrr`.
        gross_margin: Gross margin as a percentage (0-100), or `None`.
        ebitda: EBITDA, or `None`.
        burn_rate: Monthly cash burn rate, or `None`.
        runway_months: Months of runway remaining. Computed as
            `cash / burn_rate` when both are available; `None`
            otherwise.
        cash: Cash on hand, or `None`.
        customers: Number of customers, or `None`.
        growth_rate: Revenue or user growth rate as a percentage
            (can be negative), or `None`.
        cac: Customer acquisition cost, or `None`.
        ltv: Customer lifetime value, or `None`.
        valuation: Company valuation, or `None`.
        confidence_score: A 0.0-1.0 score reflecting what fraction of
            the extractable fields the AI was able to populate. Not
            provided by the AI itself; computed by
            `FinancialAnalysisService` from the extraction result, to
            avoid the AI hallucinating a confidence figure.
        created_at: Timezone-aware timestamp when the record was first
            created.
        document: The related `Document`.
    """

    __tablename__ = "financial_metrics"

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
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    arr: Mapped[float | None] = mapped_column(Float, nullable=True)
    mrr: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    burn_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    runway_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    cash: Mapped[float | None] = mapped_column(Float, nullable=True)
    customers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    growth_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    cac: Mapped[float | None] = mapped_column(Float, nullable=True)
    ltv: Mapped[float | None] = mapped_column(Float, nullable=True)
    valuation: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="financial_metrics")

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the metrics record.

        Returns:
            A string identifying the record by document id.
        """
        return f"<FinancialMetrics document_id={self.document_id}>"