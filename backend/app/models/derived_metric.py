"""SQLAlchemy ORM model for persisted derived-metric calculation results."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class DerivedMetric(Base):
    """A single persisted result from `derived_metrics_service.py`.

    Persisted (rather than recomputed on every request) per the
    provenance requirement that calculated data be stored, not
    reconstructed ad hoc. All rows for a document are replaced whenever
    metrics are recalculated (e.g. after new financial facts are
    added), mirroring the reindex pattern used elsewhere.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The document this metric was calculated for.
        metric: The metric identifier (e.g. `"revenue_yoy_growth"`).
        period: The period this result applies to, or `None`.
        value: The computed value, or `None` if not `CALCULATED`.
        display_value: The formatted display string, or `None`.
        formula: A human-readable description of the calculation.
        inputs: The facts used, as JSON (matches
            `MetricInputRef.model_dump()` shape).
        status: The `MetricStatus` value, as a string.
        confidence: A 0.0-1.0 confidence, or `None`.
        notes: Explanatory notes, or `None`.
        calculation_version: A version tag for the calculation logic
            that produced this row, for auditability.
        created_at: Timezone-aware timestamp when this result was
            recorded.
        document: The related `Document`.
    """

    __tablename__ = "derived_metrics"

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
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    display_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    inputs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="derived_metric_rows")

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the metric row.

        Returns:
            A string identifying the row by document id, metric, and
            status.
        """
        return (
            f"<DerivedMetric document_id={self.document_id} "
            f"metric={self.metric} status={self.status}>"
        )