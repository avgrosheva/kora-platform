"""SQLAlchemy ORM model for deterministic consistency/anomaly findings."""

import enum
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


class FindingSeverity(str, enum.Enum):
    """How serious a validation finding is.

    Attributes:
        INFO: Worth noting, not necessarily a problem (e.g. an unusual
            but plausible ratio).
        WARNING: A likely issue that should be investigated before
            relying on the affected figures.
        CRITICAL: A strong signal of a data-quality problem or
            materially misleading figure (e.g. EBITDA exceeding
            revenue).
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ValidationFinding(Base):
    """A single deterministic consistency or anomaly finding for a document.

    Produced by `validation_service.py`'s rule engine — never by an
    LLM. Findings are re-generated (replacing prior ones) each time
    validation is re-run, mirroring the reindex-on-rerun pattern already
    used by `DocumentAnalysis` and `InvestmentScore`.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The document this finding applies to.
        severity: How serious this finding is.
        category: A short machine-readable grouping (e.g.
            `"financial_consistency"`, `"customer_metrics"`).
        title: A short, human-readable summary.
        description: A full explanation of the finding, referencing the
            specific values involved.
        affected_metrics: The `FinancialMetricType` values (as strings)
            this finding concerns.
        sources: A list of `SourceCitation` ids supporting this finding,
            if applicable. Empty when the finding is purely a
            cross-metric consistency check with no single citation.
        suggested_question: A specific question an investor could ask
            the company to resolve this finding, or `None` if not
            applicable.
        created_at: Timezone-aware timestamp when this finding was
            recorded.
        document: The related `Document`.
    """

    __tablename__ = "validation_findings"

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
    severity: Mapped[FindingSeverity] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_metrics: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    sources: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    suggested_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="validation_findings")

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the finding.

        Returns:
            A string identifying the finding by document id, severity,
            and title.
        """
        return (
            f"<ValidationFinding document_id={self.document_id} "
            f"severity={self.severity} title={self.title!r}>"
        )