"""Pydantic schemas for citation-hardened AI extraction.

Every extracted value the AI returns through this module is wrapped in
`CitedValue`, carrying its supporting quote, page number, and
confidence alongside the value itself — never a bare string or number.
This is the schema-hardening Section 11 requires: the model cannot
return a fact without also stating where it came from.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.models.financial_fact import FinancialMetricType, FinancialValueType, PeriodType
from app.models.qualitative_fact import QualitativeFactCategory, QualitativeFactSeverityHint

T = TypeVar("T")


class CitedValue(BaseModel, Generic[T]):
    """A single extracted value with its supporting citation.

    Attributes:
        value: The extracted value, or `None` if not found in the
            document (the model must say so explicitly rather than
            omitting the field).
        quote: The exact supporting passage from the source document,
            or `None` if `value` is `None`.
        page_number: The page the quote appears on, or `None` if not
            determinable or not applicable.
        confidence: The model's confidence in this specific extraction
            (0.0-1.0), or `None` if `value` is `None`.
    """

    model_config = ConfigDict(extra="forbid")

    value: T | None
    quote: str | None = None
    page_number: int | None = None
    confidence: float | None = None


class CitedQualitativeFact(BaseModel):
    """A single structured, non-numeric claim with its citation.

    This is the Evidence Layer plan's Step 4 fix: `main_risks` and
    `growth_opportunities` above are free-text strings with no
    category or severity a downstream consumer (Coverage, Findings)
    can act on. `qualitative_facts` on `CitedBusinessAnalysisResult`
    asks the same extraction call for the same underlying claims again,
    but structured — categorized, with a severity signal where
    applicable — instead of asking the model for a second, separate
    interpretation of the document.

    Attributes:
        category: Which domain this claim concerns.
        claim_text: The claim, in the model's own normalized words.
        severity_hint: How concerning this claim is, or `None` if
            severity doesn't apply (e.g. an `OPPORTUNITY` claim).
        quote: The exact, verbatim supporting passage.
        page_number: The page the quote appears on, or `None`.
        confidence: The model's confidence in this specific claim.
    """

    model_config = ConfigDict(extra="forbid")

    category: QualitativeFactCategory
    claim_text: str
    severity_hint: QualitativeFactSeverityHint | None
    quote: str
    page_number: int | None
    confidence: float


class CitedBusinessAnalysisResult(BaseModel):
    """Citation-hardened business analysis, mirroring `AIAnalysisResult`
    field-for-field but with every value wrapped in `CitedValue`.

    Array fields (`key_products`, `competitors`, etc.) are lists of
    `CitedValue[str]` rather than `list[str]`, so each individual item
    — each competitor, each risk — carries its own citation, per
    Section 1's requirement that array items have independent
    provenance.

    `qualitative_facts` is additive on top of `main_risks`/
    `growth_opportunities`, not a replacement for them: those two
    remain exactly as they were (still map to `DocumentAnalysis.risks`/
    `opportunities`, still what the Checks tab and due-diligence report
    read), while `qualitative_facts` is the new, structured,
    category-and-severity-bearing view of the same underlying claims
    that `EvidenceService`/`FindingsService` read instead.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: CitedValue[str]
    industry: CitedValue[str]
    business_model: CitedValue[str]
    summary: CitedValue[str]
    key_products: list[CitedValue[str]]
    revenue_streams: list[CitedValue[str]]
    target_customers: list[CitedValue[str]]
    competitors: list[CitedValue[str]]
    main_risks: list[CitedValue[str]]
    growth_opportunities: list[CitedValue[str]]
    qualitative_facts: list[CitedQualitativeFact]


class CitedFinancialFactItem(BaseModel):
    """A single time-series financial fact with its citation.

    Unlike the flat `FinancialExtractionResult` (one value per metric),
    this represents ONE fact for ONE period — the model returns a list
    of these, one per (metric, period) combination it found, which is
    what makes multi-year figures like MarketGo's 2023/2024/2025
    revenue representable at all.

    Attributes:
        metric: Which financial/operating metric this is.
        value: The numeric value.
        currency: The ISO 4217 currency code, or `None` if not
            applicable.
        period_type: The granularity of `period`.
        period: The specific period string, or `None`.
        value_type: Actual/forecast/target/estimate/derived. The model
            must classify this explicitly rather than defaulting to
            actual.
        quote: The exact supporting passage.
        page_number: The page the quote appears on, or `None`.
        confidence: The model's confidence in this extraction.
    """

    model_config = ConfigDict(extra="forbid")

    metric: FinancialMetricType
    value: float
    currency: str | None
    period_type: PeriodType
    period: str | None
    value_type: FinancialValueType
    quote: str
    page_number: int | None
    confidence: float


class CitedFinancialFactsResult(BaseModel):
    """The full list of time-series financial facts extracted from a document.

    Attributes:
        facts: All distinguishable (metric, period, value_type) facts
            the model found. Never includes calculated/derived values —
            those belong to `derived_metrics_service.py`, computed
            deterministically in Python, never by the model.
    """

    model_config = ConfigDict(extra="forbid")

    facts: list[CitedFinancialFactItem]