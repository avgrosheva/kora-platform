"""Pydantic schemas for organization-wide portfolio analytics."""

import uuid

from pydantic import BaseModel


class PortfolioSummary(BaseModel):
    """Top-level portfolio statistics for an organization.

    Averages are computed only over companies (documents) with a
    non-null value for that field; a company missing a given metric
    does not pull the average toward zero.

    Attributes:
        company_count: The total number of company profiles (documents)
            in the organization.
        average_investment_score: The average overall investment score
            across scored companies, or `None` if none are scored.
        average_arr: The average ARR across companies with a known ARR,
            or `None`.
        average_valuation: The average valuation across companies with
            a known valuation, or `None`.
        average_runway: The average runway, in months, across companies
            with a known runway, or `None`.
        average_growth: The average growth rate (%) across companies
            with a known growth rate, or `None`.
        average_burn_rate: The average monthly burn rate across
            companies with a known burn rate, or `None`.
    """

    company_count: int
    average_investment_score: float | None
    average_arr: float | None
    average_valuation: float | None
    average_runway: float | None
    average_growth: float | None
    average_burn_rate: float | None


class PortfolioCompany(BaseModel):
    """A single company (document) profile, as used in portfolio rankings.

    Attributes:
        document_id: The id of the underlying document.
        company_name: The company's name, or `None` if not identified.
        industry: The company's industry, or `None` if not identified.
        overall_score: The company's overall investment score (0-100),
            or `None` if not yet scored.
        arr: Annual recurring revenue, or `None`.
        valuation: Company valuation, or `None`.
        runway_months: Months of runway remaining, or `None`.
        growth_rate: Growth rate (%), or `None`.
        burn_rate: Monthly cash burn rate, or `None`.
        confidence_score: The investment score's confidence (0.0-1.0),
            or `None`.
        currency: The ISO 4217 currency code for monetary fields, or
            `None`.
    """

    document_id: uuid.UUID
    company_name: str | None
    industry: str | None
    overall_score: float | None
    arr: float | None
    valuation: float | None
    runway_months: float | None
    growth_rate: float | None
    burn_rate: float | None
    confidence_score: float | None
    currency: str | None


class PortfolioOverview(BaseModel):
    """Deterministic company rankings across several dimensions.

    Every list is capped at 10 entries and ordered as named. All
    rankings are pure SQL `ORDER BY ... LIMIT 10` queries — no AI, no
    randomness.

    Attributes:
        top_10_companies: The 10 companies with the highest
            `overall_score`.
        worst_10_companies: The 10 companies with the lowest
            `overall_score` (among those that have been scored).
        highest_growth_companies: The 10 companies with the highest
            `growth_rate`.
        highest_arr_companies: The 10 companies with the highest `arr`.
        highest_valuation_companies: The 10 companies with the highest
            `valuation`.
        lowest_runway_companies: The 10 companies with the lowest
            `runway_months` (among those with a known runway) — the
            most at-risk on a cash-runway basis.
        highest_burn_companies: The 10 companies with the highest
            `burn_rate`.
    """

    top_10_companies: list[PortfolioCompany]
    worst_10_companies: list[PortfolioCompany]
    highest_growth_companies: list[PortfolioCompany]
    highest_arr_companies: list[PortfolioCompany]
    highest_valuation_companies: list[PortfolioCompany]
    lowest_runway_companies: list[PortfolioCompany]
    highest_burn_companies: list[PortfolioCompany]


class PortfolioRisk(BaseModel):
    """Portfolio-wide risk indicators, as counts of affected companies.

    Attributes:
        companies_at_risk: Companies flagged as at-risk overall — those
            with either low runway or a low risk sub-score (see
            `PortfolioService.AT_RISK_RUNWAY_THRESHOLD_MONTHS` and
            `PortfolioService.AT_RISK_SCORE_THRESHOLD`).
        companies_with_negative_growth: Companies with a known, strictly
            negative growth rate.
        companies_with_low_runway: Companies with a known runway below
            `PortfolioService.LOW_RUNWAY_THRESHOLD_MONTHS`.
        companies_without_recent_documents: Companies whose profile
            (document) has not been created or updated within
            `PortfolioService.STALE_THRESHOLD_DAYS` days — i.e. stale
            data, since this data model has no separate document
            history per company (see module docstring in
            `portfolio_service.py`).
        high_confidence_companies: Companies whose investment score has
            a confidence at or above
            `PortfolioService.HIGH_CONFIDENCE_THRESHOLD`.
    """

    companies_at_risk: int
    companies_with_negative_growth: int
    companies_with_low_runway: int
    companies_without_recent_documents: int
    high_confidence_companies: int


class PortfolioDistribution(BaseModel):
    """Distribution of companies across score, valuation, ARR, and industry buckets.

    Attributes:
        score_buckets: Count of companies per investment-score range
            (e.g. `"0-20"`, `"21-40"`, ..., `"81-100"`).
        valuation_buckets: Count of companies per valuation range.
        arr_buckets: Count of companies per ARR range.
        industry_distribution: Count of companies per identified
            industry. Companies with no identified industry are
            grouped under `"Unknown"`.
        country_distribution: Count of companies per country. Always
            empty in the current data model, since no country field
            exists anywhere in the schema yet — see the module
            docstring in `portfolio_service.py`. Included so the field
            is ready to populate without an API change once a country
            data source exists.
    """

    score_buckets: dict[str, int]
    valuation_buckets: dict[str, int]
    arr_buckets: dict[str, int]
    industry_distribution: dict[str, int]
    country_distribution: dict[str, int]


class PortfolioResponse(BaseModel):
    """Complete, dashboard-ready portfolio response for `GET /portfolio`.

    Attributes:
        summary: Top-level portfolio statistics.
        overview: Company rankings across several dimensions.
        risk: Portfolio-wide risk indicator counts.
        distribution: Company counts across score, valuation, ARR,
            industry, and country buckets.
    """

    summary: PortfolioSummary
    overview: PortfolioOverview
    risk: PortfolioRisk
    distribution: PortfolioDistribution