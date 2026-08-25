"""Upgraded due diligence report assembly (Section 7).

Wraps the existing `DueDiligenceService.generate_report` (unchanged,
still the source of the 16 narrative sections and LLM call) and adds
three things that are deliberately NOT delegated to the LLM:

1. `verified_facts` — pulled directly from `FinancialFact`/
   `DerivedMetric` rows, never re-asked of the model.
2. `red_flags` — surfaced from already-computed `ValidationFinding`
   rows (Section 4's engine), not re-derived by the LLM.
3. `founder_questions` — generated deterministically from
   `FindingsService` (deterministic checks, document-stated risk claims,
   and Kora's inferences — Evidence Layer plan, Step 9 rewrite: each
   question now references the actual evidence/explanation text behind
   it rather than a generic per-category template) plus
   `MissingInformationItem`'s `recommended_request` for genuinely
   missing checklist fields, where there is no extracted value to
   reference in the first place.
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
from app.services.findings_service import Finding, FindingSeverity, FindingType, FindingsService
from app.services.missing_information_service import get_recommended_request

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


def _priority_for_severity(severity: FindingSeverity) -> str:
    """Map a Finding's 5-level severity onto FounderQuestion's 2-level priority."""
    return "high" if severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH) else "medium"


def _question_from_finding(finding: Finding) -> FounderQuestion | None:
    """Build one founder question from a unified `Finding`, referencing
    its actual evidence/explanation text rather than a generic template
    (Evidence Layer plan, Step 9 — e.g. quoting the specific customer-
    concentration claim actually found, not a placeholder).

    Args:
        finding: The finding to build a question from.

    Returns:
        A `FounderQuestion`, or `None` if this finding has neither a
        ready-made `recommended_next_step` nor evidence text to quote.
    """
    priority = _priority_for_severity(finding.severity)

    if finding.type == FindingType.DETERMINISTIC and finding.recommended_next_step:
        # validation_service.py's suggested_question already references
        # the specific values involved (e.g. the actual EBITDA/revenue
        # figures) — used as-is.
        return FounderQuestion(question=finding.recommended_next_step, category=finding.category, priority=priority)

    if finding.type == FindingType.AI_INFERRED and finding.recommended_next_step:
        return FounderQuestion(
            question=f'{finding.recommended_next_step} (Kora-inferred from: "{finding.evidence}")',
            category=finding.category, priority=priority,
        )

    if finding.type == FindingType.DOCUMENT_STATED and finding.evidence:
        # No ready-made question exists for a document-stated claim
        # (Step 5 deliberately left recommended_next_step None here) --
        # build one that quotes the actual claim text, so the founder
        # sees exactly what prompted the question.
        return FounderQuestion(
            question=f'You mentioned: "{finding.evidence}" — can you share more detail and any mitigation plan?',
            category=finding.category, priority=priority,
        )

    return None


async def _build_founder_questions(
    db: AsyncSession, document_id: uuid.UUID
) -> list[FounderQuestion]:
    """Generate founder questions deterministically from findings and gaps.

    Args:
        db: The active database session.
        document_id: The document's id.

    Returns:
        Up to 10 questions, most severe findings first: one per
        finding that yields a question (see `_question_from_finding`),
        plus one per missing checklist field in a curated set of
        categories, using that field's `recommended_request` (Step 9)
        rather than a fixed per-field template — there being no
        extracted value to reference is exactly why these fall back to
        a well-justified generic request instead.
    """
    findings = await FindingsService.get_findings(db, document_id)
    severity_order = {
        FindingSeverity.CRITICAL: 0, FindingSeverity.HIGH: 1, FindingSeverity.MEDIUM: 2,
        FindingSeverity.LOW: 3, FindingSeverity.INFORMATIONAL: 4,
    }
    findings_by_severity = sorted(findings, key=lambda f: severity_order[f.severity])

    missing_result = await db.execute(
        select(MissingInformationItem).where(
            MissingInformationItem.document_id == document_id,
            MissingInformationItem.status == "missing",
            MissingInformationItem.category.in_(["team", "investment", "legal", "customers"]),
        )
    )
    missing_items = list(missing_result.scalars().all())

    questions: list[FounderQuestion] = [
        question for finding in findings_by_severity
        if (question := _question_from_finding(finding)) is not None
    ]

    for item in missing_items:
        recommended_request = get_recommended_request(item.field_name)
        if recommended_request:
            questions.append(FounderQuestion(question=recommended_request, category=item.category, priority="medium"))

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