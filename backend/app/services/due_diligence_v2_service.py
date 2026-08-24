"""Upgraded due diligence report assembly (Section 7).

Wraps the existing `DueDiligenceService.generate_report` (unchanged,
still the source of the 16 narrative sections and LLM call) and adds
three things that are deliberately NOT delegated to the LLM:

1. `verified_facts` — pulled directly from `FinancialFact`/
   `DerivedMetric` rows, never re-asked of the model.
2. `red_flags` — surfaced from already-computed `ValidationFinding`
   rows (Section 4's engine), not re-derived by the LLM.
3. `founder_questions` — generated deterministically from
   `MissingInformationItem` + `ValidationFinding` rows.
4. `recommendation_status` — computed by fixed rules over findings/
   coverage, not chosen by the model.

This adds ZERO new AI calls beyond what `DueDiligenceService.generate_report`
already makes — everything new here is assembled from already-persisted
data.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_fact import FinancialFact
from app.models.missing_information_item import MissingInformationItem
from app.models.validation_finding import ValidationFinding
from app.schemas.due_diligence_v2 import (
    DueDiligenceV2Response,
    FounderQuestion,
    RecommendationStatus,
    VerifiedFact,
)
from app.schemas.validation import ValidationFindingRead
from app.services.due_diligence_service import DueDiligenceService

# Facts surfaced in the executive summary, in display order.
_VERIFIED_FACT_METRICS = [
    ("revenue", "Revenue"),
    ("arr", "ARR"),
    ("ebitda", "EBITDA"),
    ("cash", "Cash on Hand"),
    ("cac", "CAC"),
    ("ltv", "LTV"),
    ("valuation_post_money", "Valuation"),
]


def _format_value(metric: str, value: float, currency: str | None) -> str:
    """Format a raw metric value for display in the executive summary.

    Args:
        metric: The metric identifier.
        value: The raw numeric value.
        currency: The ISO 4217 currency code, or `None`.

    Returns:
        A human-readable formatted string.
    """
    if metric in ("gross_margin", "growth_rate", "churn_rate", "retention_rate"):
        return f"{value * 100:.1f}%"
    symbol = "$" if (currency or "USD") == "USD" else f"{currency} "
    if abs(value) >= 1_000_000:
        return f"{symbol}{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{symbol}{value / 1_000:.1f}K"
    return f"{symbol}{value:,.2f}"


async def _build_verified_facts(db: AsyncSession, document_id: uuid.UUID) -> list[VerifiedFact]:
    """Pull the latest value for each headline metric directly from storage.

    Args:
        db: The active database session.
        document_id: The document's id.

    Returns:
        Verified facts for whichever headline metrics have data,
        skipping any with none — never fabricating a placeholder.
    """
    result = await db.execute(
        select(FinancialFact).where(FinancialFact.document_id == document_id)
    )
    facts = list(result.scalars().all())

    verified: list[VerifiedFact] = []
    for metric_key, label in _VERIFIED_FACT_METRICS:
        matches = [f for f in facts if f.metric == metric_key]
        if not matches:
            continue
        latest = sorted(matches, key=lambda f: f.period or "")[-1]
        verified.append(
            VerifiedFact(
                label=f"{label} ({latest.period})" if latest.period else label,
                value_display=_format_value(metric_key, latest.value, latest.currency),
                source_citation_id=str(latest.source_citation_id) if latest.source_citation_id else None,
            )
        )
    return verified


async def _build_founder_questions(
    db: AsyncSession, document_id: uuid.UUID
) -> list[FounderQuestion]:
    """Generate founder questions deterministically from findings and gaps.

    Args:
        db: The active database session.
        document_id: The document's id.

    Returns:
        Up to 10 questions: one per validation finding that has a
        `suggested_question`, plus one per missing critical checklist
        field, high-priority findings first.
    """
    findings_result = await db.execute(
        select(ValidationFinding).where(ValidationFinding.document_id == document_id)
    )
    findings = list(findings_result.scalars().all())

    missing_result = await db.execute(
        select(MissingInformationItem).where(
            MissingInformationItem.document_id == document_id,
            MissingInformationItem.status == "missing",
            MissingInformationItem.category.in_(["team", "investment", "legal", "customers"]),
        )
    )
    missing_items = list(missing_result.scalars().all())

    questions: list[FounderQuestion] = []
    for finding in findings:
        if finding.suggested_question:
            priority = "high" if finding.severity == "critical" else "medium"
            questions.append(
                FounderQuestion(question=finding.suggested_question, category=finding.category, priority=priority)
            )

    field_question_templates = {
        "founders": "Who are the founders and what is their background?",
        "key_executives": "Who are the key executives on the team?",
        "headcount": "What is the current headcount?",
        "cap_table": "Can you share the current cap table?",
        "retention": "What is customer retention over time?",
        "material_litigation": "Is the company party to any material litigation?",
    }
    for item in missing_items:
        template = field_question_templates.get(item.field_name)
        if template:
            questions.append(FounderQuestion(question=template, category=item.category, priority="medium"))

    return questions[:10]


def _compute_recommendation_status(
    findings: list[ValidationFinding], overall_score: float | None
) -> RecommendationStatus:
    """Determine a structured recommendation status from fixed rules.

    Args:
        findings: The document's validation findings.
        overall_score: The document's investment score, or `None`.

    Returns:
        A `RecommendationStatus`, never chosen by an LLM.
    """
    has_critical = any(f.severity == "critical" for f in findings)
    has_warning = any(f.severity == "warning" for f in findings)

    if has_critical:
        return RecommendationStatus.CONCERNS_IDENTIFIED
    if overall_score is None:
        return RecommendationStatus.NEEDS_MORE_INFO
    if overall_score >= 70 and not has_warning:
        return RecommendationStatus.STRONG_CANDIDATE
    if overall_score >= 50:
        return RecommendationStatus.WORTH_EXPLORING
    return RecommendationStatus.NEEDS_MORE_INFO


class DueDiligenceV2Service:
    """Assembles the upgraded, evidence-grounded due diligence report."""

    @staticmethod
    async def generate_report_v2(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID, top_k: int
    ) -> DueDiligenceV2Response:
        """Generate the upgraded due diligence report.

        Makes exactly the same AI calls as
        `DueDiligenceService.generate_report` (one embedding call, one
        LLM call) — every addition here is assembled from already-
        persisted data, adding zero AI calls.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.
            top_k: The number of retrieved excerpts to use as context.

        Returns:
            The upgraded report.

        Raises:
            Same exceptions as `DueDiligenceService.generate_report`.
        """
        base_report = await DueDiligenceService.generate_report(db, document_id, actor_id, top_k)

        verified_facts = await _build_verified_facts(db, document_id)
        founder_questions = await _build_founder_questions(db, document_id)

        findings_result = await db.execute(
            select(ValidationFinding)
            .where(ValidationFinding.document_id == document_id)
            .order_by(ValidationFinding.severity)
        )
        findings = list(findings_result.scalars().all())

        from app.models.investment_score import InvestmentScore
        score_result = await db.execute(
            select(InvestmentScore.overall_score).where(InvestmentScore.document_id == document_id)
        )
        overall_score = score_result.scalar_one_or_none()

        recommendation_status = _compute_recommendation_status(findings, overall_score)

        return DueDiligenceV2Response(
            document_id=document_id,
            recommendation_status=recommendation_status,
            executive_summary=next(
                (s.content for s in base_report.sections if s.title == "Executive Summary"), ""
            ),
            verified_facts=verified_facts,
            sections=base_report.sections,
            red_flags=[ValidationFindingRead.model_validate(f) for f in findings],
            founder_questions=founder_questions,
            sources=base_report.sources,
            model_used=base_report.model_used,
        )