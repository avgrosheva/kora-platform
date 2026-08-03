"""SQLAlchemy ORM model for time-series financial facts.

Replaces the implicit assumption in `FinancialMetrics` that each document
has exactly one value per metric. A `FinancialFact` is a single reported
or derived number for one metric, one period, with an explicit value
type (actual/forecast/target/estimate/derived) — so "2025 revenue" and
"expected 2026 revenue" are distinct, queryable rows rather than
collapsed into one column.

`FinancialMetrics` (the existing flat table) is NOT replaced or
deprecated by this model. It remains the source of truth for all
existing API responses and continues to be populated exactly as before.
`FinancialFact` is additive: a richer, time-series-capable layer that
new endpoints (`GET /documents/{id}/metrics`) and the derived-metrics
engine read from, without breaking any existing consumer.
"""

import enum
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
    from app.models.source_citation import SourceCitation


class FinancialMetricType(str, enum.Enum):
    """The kind of financial or operating fact a `FinancialFact` row records.

    This list covers the metrics named across the Phase 1 specification
    (growth, profitability, unit-economics, and valuation inputs). It is
    deliberately a fixed enum, matching this project's established
    convention for constrained fields (see `MembershipRole`,
    `DocumentStatus`) — extending it requires a migration, which is an
    acceptable tradeoff for the type-safety and query-ability it buys
    across the derived-metrics and validation engines.

    Only raw, source-reported (or directly stated) values belong here.
    Calculated values (e.g. YoY growth, CAGR, LTV/CAC) are never stored
    as facts — they are `DerivedMetric` rows instead, keeping the
    "facts vs. calculated vs. inferred" distinction structural rather
    than a matter of convention.
    """

    REVENUE = "revenue"
    GROSS_PROFIT = "gross_profit"
    GROSS_MARGIN = "gross_margin"
    EBITDA = "ebitda"
    NET_INCOME = "net_income"
    OPERATING_EXPENSES = "operating_expenses"
    CASH = "cash"
    DEBT = "debt"
    BURN_RATE = "burn_rate"
    CAC = "cac"
    LTV = "ltv"
    AOV = "aov"
    ORDERS = "orders"
    REGISTERED_CUSTOMERS = "registered_customers"
    MONTHLY_ACTIVE_USERS = "monthly_active_users"
    CHURN_RATE = "churn_rate"
    RETENTION_RATE = "retention_rate"
    FUNDING_AMOUNT = "funding_amount"
    VALUATION_PRE_MONEY = "valuation_pre_money"
    VALUATION_POST_MONEY = "valuation_post_money"


class PeriodType(str, enum.Enum):
    """The time granularity a `FinancialFact`'s `period` string represents.

    Attributes:
        MONTH: `period` is a month, e.g. `"2025-06"`.
        QUARTER: `period` is a quarter, e.g. `"2025-Q2"`.
        YEAR: `period` is a calendar year, e.g. `"2025"`.
        POINT_IN_TIME: `period` is a specific date, e.g. `"2025-06-30"`
            (used for balance-sheet-style facts like cash on hand).
        UNKNOWN: The source document did not make the period explicit.
    """

    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    POINT_IN_TIME = "point_in_time"
    UNKNOWN = "unknown"


class FinancialValueType(str, enum.Enum):
    """Whether a `FinancialFact`'s value is actual, projected, or derived.

    Attributes:
        ACTUAL: A historical, realized value.
        FORECAST: A forward-looking projection stated by the source.
        TARGET: A stated goal, not a projection or historical fact.
        ESTIMATE: An approximation explicitly flagged as such by the
            source (e.g. "LTV is estimated at around $170").
        DERIVED: Computed by Kora rather than stated directly. Included
            here (rather than only in `DerivedMetric`) so a
            `FinancialFact` row can represent a value Kora had to
            back-calculate from other facts in the same document (e.g.
            gross profit from revenue and gross margin), while still
            keeping it queryable alongside actual/reported facts.
    """

    ACTUAL = "actual"
    FORECAST = "forecast"
    TARGET = "target"
    ESTIMATE = "estimate"
    DERIVED = "derived"


class FinancialFact(Base):
    """A single time-series financial or operating fact for a document.

    Each row is one metric, one period, one value type — e.g. "2025
    annual actual revenue" and "2026 annual forecast revenue" are two
    separate rows, never collapsed into one. This is the structural
    fix for the flat single-period model's inability to represent
    growth, CAGR, or actual-vs-forecast distinctions.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The document this fact was extracted from.
        metric: Which financial/operating metric this is.
        value: The numeric value.
        currency: The ISO 4217 currency code, or `None` if not
            applicable (e.g. counts like `registered_customers`).
        period_type: The granularity of `period`.
        period: The specific period string (e.g. `"2025"`,
            `"2025-Q2"`, `"2025-06-30"`), or `None` if `period_type` is
            `UNKNOWN`.
        value_type: Whether this is an actual, forecast, target,
            estimate, or derived value.
        source_citation_id: The citation supporting this fact, or
            `None` if not yet linked to a citation.
        created_at: Timezone-aware timestamp when this fact was
            recorded.
        document: The related `Document`.
        source_citation: The related `SourceCitation`, if any.
    """

    __tablename__ = "financial_facts"

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
    metric: Mapped[FinancialMetricType] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    period_type: Mapped[PeriodType] = mapped_column(String(20), nullable=False)
    period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    value_type: Mapped[FinancialValueType] = mapped_column(String(20), nullable=False)
    source_citation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_citations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="financial_facts")
    source_citation: Mapped["SourceCitation | None"] = relationship()

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the fact.

        Returns:
            A string identifying the fact by metric, period, and value.
        """
        return (
            f"<FinancialFact document_id={self.document_id} "
            f"metric={self.metric} period={self.period} value={self.value}>"
        )