"""Organization-wide portfolio analytics.

Aggregates all "company profiles" within an organization into a single
portfolio view: summary statistics, rankings, risk indicators, and
distribution buckets. This is a pure read/aggregation layer — no AI
calls, no new persisted data. Services operate directly on
`AsyncSession` — there is no repository layer in this project's
architecture.

Data model note: this platform has no dedicated `Company` entity. A
"company profile" is an analyzed `Document` — specifically, one that
has a `DocumentAnalysis` record. This is the defining criterion for
inclusion in the portfolio: a raw upload with no analysis yet
(`status=uploaded`, `processing`, or `failed`, or simply never sent to
`POST /documents/{id}/analyze`) is not yet a company profile and is
excluded from every portfolio query below. `FinancialMetrics` and
`InvestmentScore` remain optional overlays on top of that base
population — a company profile can exist with analysis but no
financials or score computed yet, exactly as in the Dashboard milestone
(`companies_analyzed` vs `total_documents`).

Country data gap: `country_distribution` is always empty, since no
country field exists anywhere in `Document`, `DocumentAnalysis`, or
`FinancialMetrics`. This is a genuine data gap, not a bug — the field
is kept in the schema so a future country data source can populate it
without an API change.

Performance note: the entire portfolio is built from a small, fixed
number of queries regardless of organization size — one aggregate query
(counts, averages, risk counts, bucket counts), one industry
GROUP BY query, and seven bounded `ORDER BY ... LIMIT 10` ranking
queries. None of these scale with the number of company profiles in the
organization.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coverage_assessment import CoverageAssessment
from app.models.document import Document
from app.models.document_analysis import DocumentAnalysis
from app.models.financial_metrics import FinancialMetrics
from app.models.investment_score import InvestmentScore
from app.models.organization import Membership
from app.models.qualitative_fact import QualitativeFact, QualitativeFactCategory
from app.models.validation_finding import ValidationFinding
from app.schemas.portfolio import (
    PortfolioCompany,
    PortfolioDistribution,
    PortfolioDocumentRow,
    PortfolioOverview,
    PortfolioResponse,
    PortfolioRisk,
    PortfolioSummary,
)
from app.services.findings_service import (
    _QUALITATIVE_SEVERITY_TO_FINDING_SEVERITY,
    _VALIDATION_SEVERITY_TO_FINDING_SEVERITY,
    FindingSeverity,
)

RANKING_LIMIT = 10

# Risk thresholds. Chosen as reasonable, documented defaults; adjust
# here if business requirements change — every consumer reads through
# these constants rather than duplicating magic numbers.
LOW_RUNWAY_THRESHOLD_MONTHS = 6.0
AT_RISK_RUNWAY_THRESHOLD_MONTHS = 6.0
AT_RISK_SCORE_THRESHOLD = 40.0
HIGH_CONFIDENCE_THRESHOLD = 0.8
STALE_THRESHOLD_DAYS = 90

# The three categories whose QualitativeFacts each always produce one
# AI_INFERRED finding, regardless of severity_hint -- mirrors
# findings_service.py's _INFERENCE_RULES registration exactly (see
# _infer_operational_concentration_risk / _infer_ip_ownership_diligence_risk
# / _infer_team_continuity_risk). Kept as a local constant, not imported,
# since findings_service.py registers rules as functions, not category
# values -- this is this module's own translation of "which categories
# have a registered rule today", re-derived by hand if that list changes.
_INFERENCE_RULE_CATEGORIES = frozenset({
    QualitativeFactCategory.OPERATIONAL_DEPENDENCY.value,
    QualitativeFactCategory.IP_OWNERSHIP.value,
    QualitativeFactCategory.TEAM_RISK.value,
})

# Collapses FindingsService's 5-tier severity down to the 3-tier scale
# (high/medium/low) the portfolio table's open-findings badges use --
# the same scale the Checks tab's SeverityBadge already renders.
_FINDING_SEVERITY_TO_BUCKET: dict[FindingSeverity, str] = {
    FindingSeverity.CRITICAL: "high",
    FindingSeverity.HIGH: "high",
    FindingSeverity.MEDIUM: "medium",
    FindingSeverity.LOW: "low",
    FindingSeverity.INFORMATIONAL: "low",
}

_SCORE_BUCKET_LABELS = ("0-20", "21-40", "41-60", "61-80", "81-100")
_VALUATION_BUCKET_LABELS = (
    "<1M",
    "1M-10M",
    "10M-50M",
    "50M-100M",
    ">100M",
)
_ARR_BUCKET_LABELS = ("<100K", "100K-1M", "1M-5M", "5M-10M", ">10M")


class PortfolioServiceError(Exception):
    """Base exception for portfolio aggregation failures."""


class OrganizationAccessDeniedError(PortfolioServiceError):
    """Raised when the actor is not a member of the target organization.

    Raised identically whether the organization does not exist or the
    actor simply isn't a member of it. Defined locally rather than
    imported from `dashboard_service.py`, consistent with this
    project's existing pattern of each service owning its own copy of
    this exception (see `document_service.py` vs
    `organization_service.py`).
    """


async def _require_membership(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Assert that a user is a member of an organization.

    Args:
        db: The active database session.
        organization_id: The organization's id.
        user_id: The user's id.

    Raises:
        OrganizationAccessDeniedError: If no membership exists.
    """
    result = await db.execute(
        select(Membership.id).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise OrganizationAccessDeniedError("Organization not found.")


def _row_to_company(row) -> PortfolioCompany:
    """Convert a ranking query's result row into a `PortfolioCompany`.

    Args:
        row: A SQLAlchemy `Row` with the columns selected by
            `_fetch_ranked_companies`.

    Returns:
        The corresponding `PortfolioCompany`.
    """
    return PortfolioCompany(
        document_id=row.document_id,
        company_name=row.company_name,
        industry=row.industry,
        overall_score=row.overall_score,
        arr=row.arr,
        valuation=row.valuation,
        runway_months=row.runway_months,
        growth_rate=row.growth_rate,
        burn_rate=row.burn_rate,
        confidence_score=row.confidence_score,
        currency=row.currency,
    )


async def _fetch_ranked_companies(
    db: AsyncSession,
    organization_id: uuid.UUID,
    order_column: Column,
    ascending: bool,
) -> list[PortfolioCompany]:
    """Fetch the top `RANKING_LIMIT` company profiles ordered by a given column.

    A single reusable query shape backs all seven rankings exposed by
    `PortfolioOverview` — only the ordering column and direction differ.
    The base population is restricted to documents with a
    `DocumentAnalysis` (i.e. actual company profiles); `FinancialMetrics`
    and `InvestmentScore` remain optional overlays via `LEFT JOIN`.

    Args:
        db: The active database session.
        organization_id: The organization's id.
        order_column: The column to rank by (e.g.
            `InvestmentScore.overall_score`).
        ascending: If True, rank lowest-first (used for "worst" and
            "lowest runway" rankings); otherwise highest-first.

    Returns:
        Up to `RANKING_LIMIT` company profiles, ordered as requested.
        Profiles with a `None` value for `order_column` are excluded,
        since they cannot be meaningfully ranked on that dimension.
    """
    stmt = (
        select(
            Document.id.label("document_id"),
            DocumentAnalysis.company_name,
            DocumentAnalysis.industry,
            FinancialMetrics.arr,
            FinancialMetrics.valuation,
            FinancialMetrics.runway_months,
            FinancialMetrics.growth_rate,
            FinancialMetrics.burn_rate,
            FinancialMetrics.currency,
            InvestmentScore.overall_score,
            InvestmentScore.confidence_score,
        )
        .select_from(Document)
        .join(DocumentAnalysis, DocumentAnalysis.document_id == Document.id)
        .outerjoin(FinancialMetrics, FinancialMetrics.document_id == Document.id)
        .outerjoin(InvestmentScore, InvestmentScore.document_id == Document.id)
        .where(
            Document.organization_id == organization_id,
            order_column.is_not(None),
        )
        .order_by(order_column.asc() if ascending else order_column.desc())
        .limit(RANKING_LIMIT)
    )
    rows = (await db.execute(stmt)).all()
    return [_row_to_company(row) for row in rows]


async def _fetch_summary_risk_and_buckets(
    db: AsyncSession, organization_id: uuid.UUID
) -> tuple[PortfolioSummary, PortfolioRisk, dict[str, int], dict[str, int], dict[str, int]]:
    """Compute all scalar counts, averages, and bucket counts in one query.

    The base population is restricted to documents with a
    `DocumentAnalysis` (i.e. actual company profiles); `FinancialMetrics`
    and `InvestmentScore` remain optional overlays via `LEFT JOIN`.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        A tuple of `(PortfolioSummary, PortfolioRisk, score_buckets,
        valuation_buckets, arr_buckets)`.
    """
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_THRESHOLD_DAYS)

    score = InvestmentScore.overall_score
    valuation = FinancialMetrics.valuation
    arr = FinancialMetrics.arr

    stmt = (
        select(
            func.count(func.distinct(Document.id)).label("company_count"),
            func.avg(InvestmentScore.overall_score).label(
                "average_investment_score"
            ),
            func.avg(FinancialMetrics.arr).label("average_arr"),
            func.avg(FinancialMetrics.valuation).label("average_valuation"),
            func.avg(FinancialMetrics.runway_months).label("average_runway"),
            func.avg(FinancialMetrics.growth_rate).label("average_growth"),
            func.avg(FinancialMetrics.burn_rate).label("average_burn_rate"),
            func.avg(CoverageAssessment.overall_confidence * 100).label("average_coverage"),
            # --- Risk indicators ---
            func.count()
            .filter(
                (FinancialMetrics.runway_months < AT_RISK_RUNWAY_THRESHOLD_MONTHS)
                | (InvestmentScore.risk_score < AT_RISK_SCORE_THRESHOLD)
            )
            .label("companies_at_risk"),
            func.count()
            .filter(FinancialMetrics.growth_rate < 0)
            .label("companies_with_negative_growth"),
            func.count()
            .filter(FinancialMetrics.runway_months < LOW_RUNWAY_THRESHOLD_MONTHS)
            .label("companies_with_low_runway"),
            func.count()
            .filter(Document.created_at < stale_cutoff)
            .label("companies_without_recent_documents"),
            func.count()
            .filter(InvestmentScore.confidence_score >= HIGH_CONFIDENCE_THRESHOLD)
            .label("high_confidence_companies"),
            # --- Score buckets ---
            func.count().filter(score.between(0, 20)).label("score_0_20"),
            func.count().filter(score.between(21, 40)).label("score_21_40"),
            func.count().filter(score.between(41, 60)).label("score_41_60"),
            func.count().filter(score.between(61, 80)).label("score_61_80"),
            func.count().filter(score.between(81, 100)).label("score_81_100"),
            # --- Valuation buckets ---
            func.count().filter(valuation < 1_000_000).label("val_lt_1m"),
            func.count()
            .filter(valuation.between(1_000_000, 10_000_000))
            .label("val_1m_10m"),
            func.count()
            .filter(valuation.between(10_000_000, 50_000_000))
            .label("val_10m_50m"),
            func.count()
            .filter(valuation.between(50_000_000, 100_000_000))
            .label("val_50m_100m"),
            func.count().filter(valuation > 100_000_000).label("val_gt_100m"),
            # --- ARR buckets ---
            func.count().filter(arr < 100_000).label("arr_lt_100k"),
            func.count()
            .filter(arr.between(100_000, 1_000_000))
            .label("arr_100k_1m"),
            func.count()
            .filter(arr.between(1_000_000, 5_000_000))
            .label("arr_1m_5m"),
            func.count()
            .filter(arr.between(5_000_000, 10_000_000))
            .label("arr_5m_10m"),
            func.count().filter(arr > 10_000_000).label("arr_gt_10m"),
        )
        .select_from(Document)
        .join(DocumentAnalysis, DocumentAnalysis.document_id == Document.id)
        .outerjoin(FinancialMetrics, FinancialMetrics.document_id == Document.id)
        .outerjoin(InvestmentScore, InvestmentScore.document_id == Document.id)
        .outerjoin(CoverageAssessment, CoverageAssessment.document_id == Document.id)
        .where(Document.organization_id == organization_id)
    )

    row = (await db.execute(stmt)).one()

    summary = PortfolioSummary(
        company_count=row.company_count,
        average_investment_score=row.average_investment_score,
        average_arr=row.average_arr,
        average_valuation=row.average_valuation,
        average_runway=row.average_runway,
        average_growth=row.average_growth,
        average_burn_rate=row.average_burn_rate,
        average_coverage=row.average_coverage,
    )
    risk = PortfolioRisk(
        companies_at_risk=row.companies_at_risk,
        companies_with_negative_growth=row.companies_with_negative_growth,
        companies_with_low_runway=row.companies_with_low_runway,
        companies_without_recent_documents=row.companies_without_recent_documents,
        high_confidence_companies=row.high_confidence_companies,
    )
    score_buckets = dict(
        zip(
            _SCORE_BUCKET_LABELS,
            [row.score_0_20, row.score_21_40, row.score_41_60, row.score_61_80, row.score_81_100],
        )
    )
    valuation_buckets = dict(
        zip(
            _VALUATION_BUCKET_LABELS,
            [row.val_lt_1m, row.val_1m_10m, row.val_10m_50m, row.val_50m_100m, row.val_gt_100m],
        )
    )
    arr_buckets = dict(
        zip(
            _ARR_BUCKET_LABELS,
            [row.arr_lt_100k, row.arr_100k_1m, row.arr_1m_5m, row.arr_5m_10m, row.arr_gt_10m],
        )
    )

    return summary, risk, score_buckets, valuation_buckets, arr_buckets


async def _fetch_industry_distribution(
    db: AsyncSession, organization_id: uuid.UUID
) -> dict[str, int]:
    """Compute the count of company profiles per identified industry.

    The base population is restricted to documents with a
    `DocumentAnalysis` (i.e. actual company profiles).

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        A mapping of industry name to company-profile count. Profiles
        with no identified industry (an analysis exists, but its
        `industry` field is null) are grouped under `"Unknown"`.
    """
    industry_label = func.coalesce(DocumentAnalysis.industry, "Unknown").label(
        "industry"
    )
    stmt = (
        select(industry_label, func.count().label("company_count"))
        .select_from(Document)
        .join(DocumentAnalysis, DocumentAnalysis.document_id == Document.id)
        .where(Document.organization_id == organization_id)
        .group_by(industry_label)
    )
    rows = (await db.execute(stmt)).all()
    return {row.industry: row.company_count for row in rows}


async def _fetch_open_findings_by_document(
    db: AsyncSession, organization_id: uuid.UUID
) -> dict[uuid.UUID, dict[str, int]]:
    """Count open findings per document, by 3-tier severity bucket.

    Mirrors `FindingsService.get_findings`'s three sources exactly, but
    as aggregate SQL instead of one Python call per document -- this
    has to scale with an organization's full document list, not just
    one document at a time. The severity mappings are imported directly
    from `findings_service.py` rather than duplicated, so the two stay
    in sync by construction.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        A mapping of `document_id` to `{"high": n, "medium": n, "low": n}`,
        omitting zero-count severities. Documents with no findings at
        all are simply absent from the mapping.
    """
    counts: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    # 1. Deterministic -- ValidationFinding, one row per finding.
    deterministic_stmt = (
        select(
            ValidationFinding.document_id,
            ValidationFinding.severity,
            func.count().label("n"),
        )
        .join(Document, Document.id == ValidationFinding.document_id)
        .where(Document.organization_id == organization_id)
        .group_by(ValidationFinding.document_id, ValidationFinding.severity)
    )
    for row in (await db.execute(deterministic_stmt)).all():
        finding_severity = _VALIDATION_SEVERITY_TO_FINDING_SEVERITY.get(row.severity, FindingSeverity.MEDIUM)
        bucket = _FINDING_SEVERITY_TO_BUCKET[finding_severity]
        counts[row.document_id][bucket] += row.n

    # 2. Document-stated -- QualitativeFact rows with a severity_hint set.
    document_stated_stmt = (
        select(
            QualitativeFact.document_id,
            QualitativeFact.severity_hint,
            func.count().label("n"),
        )
        .join(Document, Document.id == QualitativeFact.document_id)
        .where(
            Document.organization_id == organization_id,
            QualitativeFact.severity_hint.is_not(None),
        )
        .group_by(QualitativeFact.document_id, QualitativeFact.severity_hint)
    )
    for row in (await db.execute(document_stated_stmt)).all():
        finding_severity = _QUALITATIVE_SEVERITY_TO_FINDING_SEVERITY.get(row.severity_hint, FindingSeverity.MEDIUM)
        bucket = _FINDING_SEVERITY_TO_BUCKET[finding_severity]
        counts[row.document_id][bucket] += row.n

    # 3. AI-inferred -- one finding per QualitativeFact whose category has
    # a registered inference rule, regardless of severity_hint (defaults
    # to MEDIUM when unset, exactly like the rule functions themselves).
    inferred_stmt = (
        select(
            QualitativeFact.document_id,
            QualitativeFact.severity_hint,
            func.count().label("n"),
        )
        .join(Document, Document.id == QualitativeFact.document_id)
        .where(
            Document.organization_id == organization_id,
            QualitativeFact.category.in_(_INFERENCE_RULE_CATEGORIES),
        )
        .group_by(QualitativeFact.document_id, QualitativeFact.severity_hint)
    )
    for row in (await db.execute(inferred_stmt)).all():
        finding_severity = _QUALITATIVE_SEVERITY_TO_FINDING_SEVERITY.get(row.severity_hint, FindingSeverity.MEDIUM)
        bucket = _FINDING_SEVERITY_TO_BUCKET[finding_severity]
        counts[row.document_id][bucket] += row.n

    return {document_id: dict(buckets) for document_id, buckets in counts.items()}


async def _fetch_document_rows(
    db: AsyncSession, organization_id: uuid.UUID
) -> list[PortfolioDocumentRow]:
    """Fetch every company profile in the organization as a table row.

    Unlike `_fetch_ranked_companies`, this is not capped at 10 and is
    not restricted to companies with a non-null value on some ranking
    column -- it backs the full "analyzed documents" table, which must
    show every company profile regardless of how complete its data is.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        Every company profile, newest first, each with its open
        findings already attached.
    """
    stmt = (
        select(
            Document.id.label("document_id"),
            Document.original_filename,
            Document.status,
            Document.size_bytes,
            Document.created_at,
            DocumentAnalysis.company_name,
            InvestmentScore.overall_score,
            CoverageAssessment.overall_confidence,
        )
        .select_from(Document)
        .join(DocumentAnalysis, DocumentAnalysis.document_id == Document.id)
        .outerjoin(InvestmentScore, InvestmentScore.document_id == Document.id)
        .outerjoin(CoverageAssessment, CoverageAssessment.document_id == Document.id)
        .where(Document.organization_id == organization_id)
        .order_by(Document.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    findings_by_document = await _fetch_open_findings_by_document(db, organization_id)

    return [
        PortfolioDocumentRow(
            document_id=row.document_id,
            filename=row.original_filename,
            company_name=row.company_name,
            status=row.status,
            size_bytes=row.size_bytes,
            created_at=row.created_at,
            overall_score=row.overall_score,
            coverage_percent=(
                round(row.overall_confidence * 100) if row.overall_confidence is not None else None
            ),
            open_findings=findings_by_document.get(row.document_id, {}),
        )
        for row in rows
    ]


class PortfolioService:
    """Aggregates an organization's company profiles into a portfolio view."""

    LOW_RUNWAY_THRESHOLD_MONTHS = LOW_RUNWAY_THRESHOLD_MONTHS
    AT_RISK_RUNWAY_THRESHOLD_MONTHS = AT_RISK_RUNWAY_THRESHOLD_MONTHS
    AT_RISK_SCORE_THRESHOLD = AT_RISK_SCORE_THRESHOLD
    HIGH_CONFIDENCE_THRESHOLD = HIGH_CONFIDENCE_THRESHOLD
    STALE_THRESHOLD_DAYS = STALE_THRESHOLD_DAYS

    @staticmethod
    async def get_portfolio(
        db: AsyncSession, organization_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PortfolioResponse:
        """Build the complete portfolio view for an organization.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the requesting user.

        Returns:
            The organization's `PortfolioResponse`.

        Raises:
            OrganizationAccessDeniedError: If the actor is not a member
                of the organization.
        """
        await _require_membership(db, organization_id, actor_id)

        (
            summary,
            risk,
            score_buckets,
            valuation_buckets,
            arr_buckets,
        ) = await _fetch_summary_risk_and_buckets(db, organization_id)

        industry_distribution = await _fetch_industry_distribution(
            db, organization_id
        )

        top_10 = await _fetch_ranked_companies(
            db, organization_id, InvestmentScore.overall_score, ascending=False
        )
        worst_10 = await _fetch_ranked_companies(
            db, organization_id, InvestmentScore.overall_score, ascending=True
        )
        highest_growth = await _fetch_ranked_companies(
            db, organization_id, FinancialMetrics.growth_rate, ascending=False
        )
        highest_arr = await _fetch_ranked_companies(
            db, organization_id, FinancialMetrics.arr, ascending=False
        )
        highest_valuation = await _fetch_ranked_companies(
            db, organization_id, FinancialMetrics.valuation, ascending=False
        )
        lowest_runway = await _fetch_ranked_companies(
            db, organization_id, FinancialMetrics.runway_months, ascending=True
        )
        highest_burn = await _fetch_ranked_companies(
            db, organization_id, FinancialMetrics.burn_rate, ascending=False
        )

        overview = PortfolioOverview(
            top_10_companies=top_10,
            worst_10_companies=worst_10,
            highest_growth_companies=highest_growth,
            highest_arr_companies=highest_arr,
            highest_valuation_companies=highest_valuation,
            lowest_runway_companies=lowest_runway,
            highest_burn_companies=highest_burn,
        )
        distribution = PortfolioDistribution(
            score_buckets=score_buckets,
            valuation_buckets=valuation_buckets,
            arr_buckets=arr_buckets,
            industry_distribution=industry_distribution,
            country_distribution={},
        )

        documents = await _fetch_document_rows(db, organization_id)

        return PortfolioResponse(
            summary=summary,
            overview=overview,
            risk=risk,
            distribution=distribution,
            documents=documents,
        )