"""Pydantic schemas for the organization dashboard."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DashboardSummary(BaseModel):
    """Top-level aggregate counts and averages for an organization.

    All averages are computed only over documents that have a
    `FinancialMetrics` record with a non-null value for that field;
    documents missing a given metric do not pull the average down to
    zero or `None` unless *no* document has that metric at all.

    Attributes:
        total_companies: The number of distinct company names identified
            across the organization's analyzed documents.
        total_documents: The total number of documents uploaded to the
            organization, regardless of processing or analysis status.
        companies_analyzed: The number of documents that have a
            completed business analysis (`DocumentAnalysis`).
        average_arr: The average annual recurring revenue across
            documents with a known ARR, or `None` if none have one.
        average_growth_rate: The average growth rate (%) across
            documents with a known growth rate, or `None`.
        average_burn_rate: The average monthly burn rate across
            documents with a known burn rate, or `None`.
        average_runway: The average runway, in months, across documents
            with a known runway, or `None`.
        average_valuation: The average valuation across documents with
            a known valuation, or `None`.
    """

    total_companies: int
    total_documents: int
    companies_analyzed: int
    average_arr: float | None
    average_growth_rate: float | None
    average_burn_rate: float | None
    average_runway: float | None
    average_valuation: float | None


class TopCompany(BaseModel):
    """The document/company with the highest known ARR in the organization.

    Attributes:
        document_id: The id of the document this company profile
            belongs to.
        company_name: The company's name, or `None` if not identified
            by the business analysis.
        arr: The company's annual recurring revenue. Always non-null,
            since this record only exists when at least one document
            has a known ARR (see `DashboardService.get_dashboard`).
        currency: The ISO 4217 currency code the figure is denominated
            in, or `None` if not stated.
    """

    document_id: uuid.UUID
    company_name: str | None
    arr: float
    currency: str | None


class RecentDocument(BaseModel):
    """A recently uploaded document, for the dashboard's activity feed.

    Attributes:
        id: The document's unique identifier.
        filename: The original filename as supplied by the uploader.
        status: The document's current processing status.
        created_at: Timestamp when the document was uploaded.
        organization_id: The organization the document belongs to.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: DocumentStatus
    created_at: datetime
    organization_id: uuid.UUID


class PortfolioStats(BaseModel):
    """Portfolio-wide health indicators across the organization's companies.

    Attributes:
        companies_with_positive_growth: The number of documents with a
            known, strictly positive growth rate.
        companies_with_negative_growth: The number of documents with a
            known, strictly negative growth rate.
        companies_low_runway: The number of documents with a known
            runway below `DashboardService.LOW_RUNWAY_THRESHOLD_MONTHS`.
        average_confidence_score: The average financial-extraction
            confidence score across documents with financial metrics,
            or `None` if none exist.
    """

    companies_with_positive_growth: int
    companies_with_negative_growth: int
    companies_low_runway: int
    average_confidence_score: float | None


class DashboardResponse(DashboardSummary):
    """Complete, dashboard-ready response for `GET /dashboard`.

    Inherits every field from `DashboardSummary` (flattened into this
    model's own top-level fields) and adds the top company, recent
    documents, and portfolio statistics. All computation (averages,
    rankings, thresholds) happens server-side in `DashboardService` —
    the frontend performs no calculations on this payload.

    Attributes:
        top_company: The company with the highest known ARR, or `None`
            if no document in the organization has a known ARR.
        recent_documents: The most recently uploaded documents.
        portfolio_stats: Portfolio-wide health indicators.
    """

    top_company: TopCompany | None
    recent_documents: list[RecentDocument]
    portfolio_stats: PortfolioStats