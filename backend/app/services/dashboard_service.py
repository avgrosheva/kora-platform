"""Dashboard aggregation.

Aggregates existing `Document`, `DocumentAnalysis`, and
`FinancialMetrics` records into a single dashboard-ready response. This
service performs no AI calls and creates no new persisted data — it is
a pure read/aggregation layer over data produced by earlier pipeline
stages. Services operate directly on `AsyncSession` — there is no
repository layer in this project's architecture.

Performance note: the entire dashboard is built from exactly three
queries regardless of organization size — one aggregate query (counts,
averages, portfolio-stat counts), one top-company query, and one
recent-documents query. `DocumentAnalysis` and `FinancialMetrics` are
both in a strict one-to-one relationship with `Document` (enforced by a
unique constraint on `document_id`), so `LEFT JOIN`ing them onto
`Document` never fans out rows, which is what keeps the aggregate query
correct without needing `DISTINCT` on every column or a subquery per
metric.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_analysis import DocumentAnalysis
from app.models.financial_metrics import FinancialMetrics
from app.models.organization import Membership
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardSummary,
    PortfolioStats,
    RecentDocument,
    TopCompany,
)

from app.models.investment_score import InvestmentScore
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardSummary,
    HighestGrowthCompany,
    HighestRiskCompany,
    PortfolioStats,
    RecentDocument,
    ScoredCompany,
    TopCompany,
)

RECENT_DOCUMENTS_LIMIT = 5
LOW_RUNWAY_THRESHOLD_MONTHS = 6.0
TOP_SCORED_COMPANIES_LIMIT = 5


class DashboardServiceError(Exception):
    """Base exception for dashboard aggregation failures."""


class OrganizationAccessDeniedError(DashboardServiceError):
    """Raised when the actor is not a member of the target organization.

    Raised identically whether the organization does not exist or the
    actor simply isn't a member of it, to avoid confirming the
    existence of organizations the actor has no access to. This mirrors
    the same-named exception in `document_service.py`; each service
    defines its own copy rather than sharing one, consistent with this
    project's existing pattern (see `organization_service.py` vs
    `document_service.py`).
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
        OrganizationAccessDeniedError: If no membership exists, meaning
            either the organization does not exist or the user is not a
            member of it.
    """
    result = await db.execute(
        select(Membership.id).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise OrganizationAccessDeniedError("Organization not found.")


async def _fetch_summary_and_portfolio_stats(
    db: AsyncSession, organization_id: uuid.UUID
) -> tuple[DashboardSummary, PortfolioStats, float | None]:
    """Compute all scalar counts and averages in a single aggregate query.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        A tuple of `(DashboardSummary, PortfolioStats, average_investment_score)`.
    """
    stmt = (
        select(
            func.count(func.distinct(Document.id)).label("total_documents"),
            func.count(func.distinct(DocumentAnalysis.company_name)).label(
                "total_companies"
            ),
            func.count(func.distinct(DocumentAnalysis.id)).label(
                "companies_analyzed"
            ),
            func.avg(FinancialMetrics.arr).label("average_arr"),
            func.avg(FinancialMetrics.growth_rate).label("average_growth_rate"),
            func.avg(FinancialMetrics.burn_rate).label("average_burn_rate"),
            func.avg(FinancialMetrics.runway_months).label("average_runway"),
            func.avg(FinancialMetrics.valuation).label("average_valuation"),
            func.avg(FinancialMetrics.confidence_score).label(
                "average_confidence_score"
            ),
            func.avg(InvestmentScore.overall_score).label(
                "average_investment_score"
            ),
            func.count()
            .filter(FinancialMetrics.growth_rate > 0)
            .label("companies_with_positive_growth"),
            func.count()
            .filter(FinancialMetrics.growth_rate < 0)
            .label("companies_with_negative_growth"),
            func.count()
            .filter(FinancialMetrics.runway_months < LOW_RUNWAY_THRESHOLD_MONTHS)
            .label("companies_low_runway"),
        )
        .select_from(Document)
        .outerjoin(
            DocumentAnalysis, DocumentAnalysis.document_id == Document.id
        )
        .outerjoin(
            FinancialMetrics, FinancialMetrics.document_id == Document.id
        )
        .outerjoin(
            InvestmentScore, InvestmentScore.document_id == Document.id
        )
        .where(Document.organization_id == organization_id)
    )

    row = (await db.execute(stmt)).one()

    summary = DashboardSummary(
        total_companies=row.total_companies,
        total_documents=row.total_documents,
        companies_analyzed=row.companies_analyzed,
        average_arr=row.average_arr,
        average_growth_rate=row.average_growth_rate,
        average_burn_rate=row.average_burn_rate,
        average_runway=row.average_runway,
        average_valuation=row.average_valuation,
    )
    portfolio_stats = PortfolioStats(
        companies_with_positive_growth=row.companies_with_positive_growth,
        companies_with_negative_growth=row.companies_with_negative_growth,
        companies_low_runway=row.companies_low_runway,
        average_confidence_score=row.average_confidence_score,
    )
    return summary, portfolio_stats, row.average_investment_score


async def _fetch_top_company(
    db: AsyncSession, organization_id: uuid.UUID
) -> TopCompany | None:
    """Fetch the document/company with the highest known ARR.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        The `TopCompany`, or `None` if no document in the organization
        has a known ARR.
    """
    stmt = (
        select(
            FinancialMetrics.document_id,
            FinancialMetrics.arr,
            FinancialMetrics.currency,
            DocumentAnalysis.company_name,
        )
        .select_from(FinancialMetrics)
        .join(Document, Document.id == FinancialMetrics.document_id)
        .outerjoin(
            DocumentAnalysis,
            DocumentAnalysis.document_id == FinancialMetrics.document_id,
        )
        .where(
            Document.organization_id == organization_id,
            FinancialMetrics.arr.is_not(None),
        )
        .order_by(FinancialMetrics.arr.desc())
        .limit(1)
    )

    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        return None

    return TopCompany(
        document_id=row.document_id,
        company_name=row.company_name,
        arr=row.arr,
        currency=row.currency,
    )

async def _fetch_top_scored_companies(
    db: AsyncSession, organization_id: uuid.UUID
) -> list[ScoredCompany]:
    """Fetch the documents with the highest overall investment scores.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        Up to `TOP_SCORED_COMPANIES_LIMIT` scored documents, highest
        score first.
    """
    stmt = (
        select(
            InvestmentScore.document_id,
            InvestmentScore.overall_score,
            DocumentAnalysis.company_name,
        )
        .select_from(InvestmentScore)
        .join(Document, Document.id == InvestmentScore.document_id)
        .outerjoin(
            DocumentAnalysis,
            DocumentAnalysis.document_id == InvestmentScore.document_id,
        )
        .where(
            Document.organization_id == organization_id,
            InvestmentScore.overall_score.is_not(None),
        )
        .order_by(InvestmentScore.overall_score.desc())
        .limit(TOP_SCORED_COMPANIES_LIMIT)
    )

    rows = (await db.execute(stmt)).all()
    return [
        ScoredCompany(
            document_id=row.document_id,
            company_name=row.company_name,
            overall_score=row.overall_score,
        )
        for row in rows
    ]


async def _fetch_highest_growth_company(
    db: AsyncSession, organization_id: uuid.UUID
) -> HighestGrowthCompany | None:
    """Fetch the document with the highest known growth rate.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        The `HighestGrowthCompany`, or `None` if no document has a
        known growth rate.
    """
    stmt = (
        select(
            FinancialMetrics.document_id,
            FinancialMetrics.growth_rate,
            DocumentAnalysis.company_name,
        )
        .select_from(FinancialMetrics)
        .join(Document, Document.id == FinancialMetrics.document_id)
        .outerjoin(
            DocumentAnalysis,
            DocumentAnalysis.document_id == FinancialMetrics.document_id,
        )
        .where(
            Document.organization_id == organization_id,
            FinancialMetrics.growth_rate.is_not(None),
        )
        .order_by(FinancialMetrics.growth_rate.desc())
        .limit(1)
    )

    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        return None

    return HighestGrowthCompany(
        document_id=row.document_id,
        company_name=row.company_name,
        growth_rate=row.growth_rate,
    )


async def _fetch_highest_risk_company(
    db: AsyncSession, organization_id: uuid.UUID
) -> HighestRiskCompany | None:
    """Fetch the scored document with the lowest `risk_score`.

    The lowest `risk_score` represents the highest actual risk, since
    `risk_score` measures stability/safety (higher is safer).

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        The `HighestRiskCompany`, or `None` if no document has been
        scored with a risk component.
    """
    stmt = (
        select(
            InvestmentScore.document_id,
            InvestmentScore.risk_score,
            DocumentAnalysis.company_name,
        )
        .select_from(InvestmentScore)
        .join(Document, Document.id == InvestmentScore.document_id)
        .outerjoin(
            DocumentAnalysis,
            DocumentAnalysis.document_id == InvestmentScore.document_id,
        )
        .where(
            Document.organization_id == organization_id,
            InvestmentScore.risk_score.is_not(None),
        )
        .order_by(InvestmentScore.risk_score.asc())
        .limit(1)
    )

    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        return None

    return HighestRiskCompany(
        document_id=row.document_id,
        company_name=row.company_name,
        risk_score=row.risk_score,
    )

async def _fetch_recent_documents(
    db: AsyncSession, organization_id: uuid.UUID
) -> list[RecentDocument]:
    """Fetch the most recently uploaded documents for an organization.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        Up to `RECENT_DOCUMENTS_LIMIT` documents, most recent first.
    """
    stmt = (
        select(Document)
        .where(Document.organization_id == organization_id)
        .order_by(Document.created_at.desc())
        .limit(RECENT_DOCUMENTS_LIMIT)
    )
    documents = (await db.execute(stmt)).scalars().all()
    return [RecentDocument.model_validate(document) for document in documents]


class DashboardService:
    """Aggregates organization data into a single dashboard response."""

    @staticmethod
    async def get_dashboard(
        db: AsyncSession, organization_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DashboardResponse:
        """Build the complete dashboard for an organization.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the requesting user.

        Returns:
            The organization's `DashboardResponse`.

        Raises:
            OrganizationAccessDeniedError: If the actor is not a member
                of the organization.
        """
        await _require_membership(db, organization_id, actor_id)

        summary, portfolio_stats, average_investment_score = (
            await _fetch_summary_and_portfolio_stats(db, organization_id)
        )
        top_company = await _fetch_top_company(db, organization_id)
        recent_documents = await _fetch_recent_documents(db, organization_id)
        top_scored_companies = await _fetch_top_scored_companies(
            db, organization_id
        )
        highest_growth_company = await _fetch_highest_growth_company(
            db, organization_id
        )
        highest_risk_company = await _fetch_highest_risk_company(
            db, organization_id
        )

        return DashboardResponse(
            **summary.model_dump(),
            top_company=top_company,
            recent_documents=recent_documents,
            portfolio_stats=portfolio_stats,
            top_scored_companies=top_scored_companies,
            average_investment_score=average_investment_score,
            highest_growth_company=highest_growth_company,
            highest_risk_company=highest_risk_company,
        )