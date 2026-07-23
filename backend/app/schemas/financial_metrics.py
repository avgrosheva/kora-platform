"""Pydantic schemas for AI-derived financial KPIs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FinancialMetricsCreate(BaseModel):
    """Internal DTO for persisting financial metrics, shaped for the database.

    Built by `FinancialAnalysisService` from a validated
    `FinancialExtractionResult` (see `app.services.ai_service`) after
    normalization and KPI computation. Not exposed as an API request
    body — `POST /documents/{id}/financial-analysis` takes no body,
    since the input is the document's already-stored text and analysis,
    not user-supplied data.

    Attributes:
        currency: The ISO 4217 currency code, or `None`.
        revenue: Total revenue, or `None`.
        arr: Annual recurring revenue, or `None`.
        mrr: Monthly recurring revenue, or `None`.
        gross_margin: Gross margin as a percentage, or `None`.
        ebitda: EBITDA, or `None`.
        burn_rate: Monthly cash burn rate, or `None`.
        runway_months: Computed months of runway, or `None`.
        cash: Cash on hand, or `None`.
        customers: Number of customers, or `None`.
        growth_rate: Growth rate as a percentage, or `None`.
        cac: Customer acquisition cost, or `None`.
        ltv: Customer lifetime value, or `None`.
        valuation: Company valuation, or `None`.
        confidence_score: Computed fraction (0.0-1.0) of extractable
            fields the AI populated.
    """

    currency: str | None
    revenue: float | None
    arr: float | None
    mrr: float | None
    gross_margin: float | None
    ebitda: float | None
    burn_rate: float | None
    runway_months: float | None
    cash: float | None
    customers: int | None
    growth_rate: float | None
    cac: float | None
    ltv: float | None
    valuation: float | None
    confidence_score: float | None


class FinancialMetricsRead(BaseModel):
    """Public representation of a document's financial KPIs.

    Designed to be dashboard-ready as-is: every field is a plain
    JSON-serializable scalar, with no nested structures or units
    requiring further transformation before charting or display.

    Attributes:
        id: The metrics record's unique identifier.
        document_id: The analyzed document's id.
        currency: The ISO 4217 currency code, or `None`.
        revenue: Total revenue, or `None`.
        arr: Annual recurring revenue, or `None`.
        mrr: Monthly recurring revenue, or `None`.
        gross_margin: Gross margin as a percentage, or `None`.
        ebitda: EBITDA, or `None`.
        burn_rate: Monthly cash burn rate, or `None`.
        runway_months: Months of runway remaining, or `None`.
        cash: Cash on hand, or `None`.
        customers: Number of customers, or `None`.
        growth_rate: Growth rate as a percentage, or `None`.
        cac: Customer acquisition cost, or `None`.
        ltv: Customer lifetime value, or `None`.
        valuation: Company valuation, or `None`.
        confidence_score: Fraction (0.0-1.0) of extractable fields the
            AI populated.
        created_at: Timestamp when the record was first created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    currency: str | None
    revenue: float | None
    arr: float | None
    mrr: float | None
    gross_margin: float | None
    ebitda: float | None
    burn_rate: float | None
    runway_months: float | None
    cash: float | None
    customers: int | None
    growth_rate: float | None
    cac: float | None
    ltv: float | None
    valuation: float | None
    confidence_score: float | None
    created_at: datetime