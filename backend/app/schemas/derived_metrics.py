"""Pydantic schemas for the deterministic derived-metrics engine.

These schemas define the structured output contract for every
calculated metric: `derived_metrics_service.py` never returns bare
floats — every result carries its formula, its inputs, and an explicit
status, so the frontend and any downstream consumer (chat, due
diligence) can distinguish a genuinely calculated figure from one that
couldn't be computed and why.
"""

import uuid
from enum import Enum

from pydantic import BaseModel, ConfigDict


class MetricStatus(str, Enum):
    """The outcome of attempting to compute a derived metric.

    Attributes:
        CALCULATED: Successfully computed from available facts.
        REPORTED: The value was stated directly in the source document
            rather than calculated (kept distinct per the spec's
            facts-vs-calculated distinction; not produced by this
            engine's calculator functions, but reserved for future use
            when a service echoes a source-reported figure alongside a
            calculated one for comparison).
        MISSING_INPUTS: One or more required facts were not found.
        PERIOD_MISMATCH: The required facts exist but their periods are
            not comparable (e.g. a monthly figure divided by an annual
            figure).
        AMBIGUOUS: Multiple candidate facts exist for the same
            metric/period and the engine cannot determine which to use.
        INVALID: The calculation would be mathematically invalid (e.g.
            division by zero, negative value where nonsensical).
    """

    CALCULATED = "calculated"
    REPORTED = "reported"
    MISSING_INPUTS = "missing_inputs"
    PERIOD_MISMATCH = "period_mismatch"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"


class MetricInputRef(BaseModel):
    """A single input value that contributed to a derived metric.

    Attributes:
        name: A human-readable name for this input (e.g. `"Revenue"`).
        value: The input's numeric value.
        period: The period this input value applies to, or `None`.
        source_citation_id: The id of the `SourceCitation` supporting
            this input, or `None` if not yet linked (citation linking
            is wired in a later step, once `financial_facts_service.py`
            populates `FinancialFact.source_citation_id`).
    """

    name: str
    value: float
    period: str | None
    source_citation_id: str | None = None


class DerivedMetricResult(BaseModel):
    """A single computed (or attempted) derived metric.

    Attributes:
        metric: A stable machine-readable identifier for this metric
            (e.g. `"revenue_yoy_growth"`).
        period: The period this result applies to (e.g. `"2025"` for a
            single-period metric, or `"2023-2025"` for a range like
            CAGR), or `None` if not period-specific.
        value: The computed numeric value, or `None` if `status` is not
            `CALCULATED`.
        display_value: A human-readable formatted string (e.g.
            `"141.7%"`, `"8.1x"`, `"$27.8M"`), or `None` if `status` is
            not `CALCULATED`.
        formula: A human-readable description of how this metric is
            computed (e.g. `"(Revenue[t] - Revenue[t-1]) / Revenue[t-1]"`),
            always present regardless of status, so the UI can show
            what *would* be calculated once inputs are available.
        inputs: The facts used in the calculation. Empty if `status` is
            `MISSING_INPUTS`.
        status: The outcome of attempting this calculation.
        confidence: A 0.0-1.0 confidence in this result, or `None` if
            not applicable (e.g. `MISSING_INPUTS`). Lower than 1.0 when
            any input is an `ESTIMATE`-type fact rather than `ACTUAL`.
        notes: A human-readable explanation, used especially for
            non-`CALCULATED` statuses (e.g. which inputs are missing,
            or why periods are mismatched).
    """

    model_config = ConfigDict(extra="forbid")

    metric: str
    period: str | None
    value: float | None
    display_value: str | None
    formula: str
    inputs: list[MetricInputRef]
    status: MetricStatus
    confidence: float | None
    notes: str | None = None

class DerivedMetricRead(BaseModel):
    """Public representation of a persisted derived metric.

    Attributes:
        id: The metric row's unique identifier.
        document_id: The document this metric was calculated for.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    metric: str
    period: str | None
    value: float | None
    display_value: str | None
    formula: str
    inputs: list[MetricInputRef]
    status: MetricStatus
    confidence: float | None
    notes: str | None


class MetricsResponse(BaseModel):
    """Response for `GET /documents/{id}/metrics`.

    Attributes:
        financial_facts: The document's raw time-series facts.
        derived_metrics: The document's computed derived metrics,
            grouped implicitly by metric name (frontend groups by
            growth/profitability/unit_economics/valuation via metric
            name prefix or a lookup table).
    """

    financial_facts: list[dict]
    derived_metrics: list[DerivedMetricRead]