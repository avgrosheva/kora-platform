"""SQLAlchemy ORM model for explainable analysis-coverage assessments."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Float, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class CoverageAssessment(Base):
    """Explainable coverage/confidence assessment for a document's analysis.

    Replaces reliance on a single opaque confidence percentage. One row
    per document; re-running coverage assessment updates the existing
    row rather than creating a new one, mirroring `DocumentAnalysis`.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The document this assessment covers. Unique, so
            each document has at most one assessment.
        overall_confidence: A composite 0.0-1.0 score. Never presented
            to users as an investment-quality or probability score —
            see `coverage_service.py`'s module docstring.
        coverage: Per-category coverage, e.g.
            `{"company": {"found": 8, "required": 10, "score": 0.8}, ...}`.
        source_coverage: The fraction of extracted fields that have at
            least one `SourceCitation` (0.0-1.0).
        ambiguities_count: The number of fields where extraction found
            multiple plausible candidate values.
        critical_missing_fields: Field names from
            `coverage_service.REQUIRED_FIELDS_REGISTRY` that are
            missing and considered critical for a sound assessment.
        created_at: Timezone-aware timestamp when this assessment was
            first created.
        document: The related `Document`.
    """

    __tablename__ = "coverage_assessments"

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
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    coverage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    ambiguities_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_missing_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="coverage_assessment")

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the assessment.

        Returns:
            A string identifying the assessment by document id and
            overall confidence.
        """
        return (
            f"<CoverageAssessment document_id={self.document_id} "
            f"overall_confidence={self.overall_confidence}>"
        )