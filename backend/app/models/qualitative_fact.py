"""SQLAlchemy ORM model for non-numeric, citable claims (Step 4 of the
Evidence Layer plan).

Same architectural role as `FinancialFact`, for claims that aren't a
number: customer concentration risk, legal/regulatory exposure,
operational/vendor dependency, IP ownership questions, team/key-person
risk, market risk, growth opportunities, and anything else that doesn't
fit those buckets. Each row is one claim with its own category,
severity signal, and citation, rather than an undifferentiated
free-text list.

`DocumentAnalysis.risks`/`opportunities` (plain string arrays) are NOT
replaced or deprecated by this model. They remain exactly as they are —
populated by both the plain (`/analyze`) and cited
(`/analyze-with-citations`) pipelines, and are still what the Checks tab
and the due-diligence report's narrative sections read. `QualitativeFact`
is additive: a richer, categorized, per-claim layer that only the cited
pipeline populates (see `ai_service.py`'s extended
`_CITED_BUSINESS_SYSTEM_PROMPT`), which `EvidenceService` (and, from
Step 5, `FindingsService`) read from instead of trying to infer
structure out of a plain string list.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.source_citation import SourceCitation


class QualitativeFactCategory(str, enum.Enum):
    """Which domain a qualitative claim concerns.

    Mirrors this project's fixed-enum convention for constrained fields
    (see `FinancialMetricType`, `MembershipRole`). `TEAM_RISK` and
    `MARKET_RISK` deliberately line up with `coverage_service.py`'s
    "team"/"market" checklist categories — `EvidenceService` maps them
    onto those buckets directly, so a document with a real team- or
    market-risk claim now contributes actual signal to categories that,
    before this table existed, could only ever show 0 found (no
    extraction pipeline had ever produced team- or market-scoped
    evidence at all).
    """

    CUSTOMER_RISK = "customer_risk"
    LEGAL_REGULATORY = "legal_regulatory"
    OPERATIONAL_DEPENDENCY = "operational_dependency"
    IP_OWNERSHIP = "ip_ownership"
    TEAM_RISK = "team_risk"
    MARKET_RISK = "market_risk"
    OPPORTUNITY = "opportunity"
    OTHER = "other"


class QualitativeFactType(str, enum.Enum):
    """How a qualitative fact came to be known.

    Mirrors `EvidenceFactType`'s vocabulary at the model layer, kept as
    a separate enum here (rather than importing `EvidenceFactType` from
    `evidence_service.py`) to avoid a model importing a service —
    `evidence_service.py` maps this onto `EvidenceFactType` instead.

    Attributes:
        DOCUMENT_STATED: Extracted directly from the source document.
            Every fact the cited business-analysis extraction produces
            today is this.
        AI_INFERRED: A conclusion the AI drew that goes beyond what the
            document literally states. Nothing currently writes this —
            defined for forward compatibility with a future extraction
            path that infers rather than quotes. Must always be visibly
            labeled as such wherever displayed, never presented as a
            verified fact (see `EvidenceFactType.AI_INFERRED`).
    """

    DOCUMENT_STATED = "document_stated"
    AI_INFERRED = "ai_inferred"


class QualitativeFactSeverityHint(str, enum.Enum):
    """How concerning a qualitative claim is, in the AI's own judgment.

    `None` (no severity_hint) is for facts with no risk dimension at
    all — most notably `OPPORTUNITY` claims, since a growth opportunity
    isn't "low severity," severity simply doesn't apply to it. Uses the
    same five-level vocabulary the Findings layer (Step 5 of the
    Evidence Layer plan) uses for `Finding.severity`, so a qualitative
    fact's hint can feed a `Finding` with no translation.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class QualitativeFact(Base):
    """A single non-numeric, citable claim extracted from a document.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The document this fact was extracted from.
        category: Which domain this claim concerns.
        claim_text: The claim itself, in the AI's own words (a
            normalized restatement suitable for display in a findings
            list). The verbatim supporting passage lives on the linked
            `source_citation`'s `quote`, not here.
        fact_type: How this fact came to be known.
        severity_hint: How concerning this claim is, or `None` if
            severity doesn't apply (e.g. `OPPORTUNITY` claims).
        source_citation_id: The citation supporting this fact, or
            `None` if not yet linked to one.
        confidence: The extraction's confidence in this specific claim
            (0.0-1.0), stored directly here — unlike `FinancialFact`,
            which relies solely on its citation's confidence — since
            downstream consumers (Step 5's `FindingsService`) need it
            without an extra join for every fact they read.
        created_at: Timezone-aware timestamp when this fact was
            recorded.
        document: The related `Document`.
        source_citation: The related `SourceCitation`, if any.
    """

    __tablename__ = "qualitative_facts"

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
    category: Mapped[QualitativeFactCategory] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    fact_type: Mapped[QualitativeFactType] = mapped_column(String(20), nullable=False)
    severity_hint: Mapped[QualitativeFactSeverityHint | None] = mapped_column(String(20), nullable=True)
    source_citation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_citations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="qualitative_facts")
    source_citation: Mapped["SourceCitation | None"] = relationship()

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the fact.

        Returns:
            A string identifying the fact by document id, category, and
            severity hint.
        """
        return (
            f"<QualitativeFact document_id={self.document_id} "
            f"category={self.category} severity_hint={self.severity_hint}>"
        )
