"""Regression test for Evidence Layer Bug C.

Before this fix, the due diligence report's narrative was generated
from `document.text_content` (via retrieved excerpts) plus flat
scalar/array fields only -- it never saw `FinancialFact`,
`QualitativeFact`, or `ValidationFinding` rows. The model could
therefore write "No red flags were identified" in the Red Flags
section of the SAME response that (via `DueDiligenceV2Service`)
carried a non-empty, critical `red_flags` list -- a direct
self-contradiction within one API response.

This test drives the real, database-backed pipeline: a genuine
critical `ValidationFinding` is persisted via the real validation
engine, and `AIService.generate_due_diligence_report` is mocked to
return EXACTLY the contradictory narrative from the bug report ("No
red flags were identified.") -- simulating the worst case where the
prompt-level fix (findings are now in the prompt) still didn't change
the model's behavior. The post-generation check must catch this
regardless.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P
from app.services.ai_service import DueDiligenceReportResult
from app.services.derived_metrics_service import FactPoint
from app.services.due_diligence_service import DueDiligenceService
from app.services.financial_facts_service import FinancialFactsService
from app.services.validation_service import ValidationService, run_all_validations


def _fake_report_with_no_red_flags() -> DueDiligenceReportResult:
    """Exactly reproduces the bug: every section is minimal, and Red
    Flags explicitly claims nothing was found."""
    return DueDiligenceReportResult(
        executive_summary="A brief summary.",
        company_overview="Overview.",
        problem="Problem.",
        solution="Solution.",
        business_model="Business model.",
        market="Market.",
        competition="Competition.",
        traction="Traction.",
        financial_analysis="Financial analysis.",
        growth="Growth.",
        risks="No significant risks were identified.",
        red_flags="No red flags were identified.",
        investment_thesis="Thesis.",
        recommendation="Recommendation.",
        confidence_level="Moderate.",
        open_questions="None.",
    )


@pytest.mark.asyncio(loop_scope="session")
class TestDueDiligenceBugC:
    async def test_report_no_longer_contradicts_a_critical_finding(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        # A genuine, EBITDA > revenue critical inconsistency, run
        # through the real, unmodified validation engine -- not a mock.
        facts = [
            FactPoint(metric=M.REVENUE, value=4_000_000, period="2025", period_type=P.YEAR, value_type=V.ACTUAL),
            FactPoint(metric=M.EBITDA, value=5_000_000, period="2025", period_type=P.YEAR, value_type=V.ACTUAL),
        ]
        await FinancialFactsService.replace_facts(db_session, document_id, [
            {"metric": f.metric, "value": f.value, "period": f.period, "period_type": f.period_type,
             "value_type": f.value_type, "currency": "USD"}
            for f in facts
        ])
        validation_findings = run_all_validations(facts)
        assert any(f.severity.value == "critical" for f in validation_findings), (
            "Fixture assumption: EBITDA > revenue must be a critical finding "
            "for this test to actually exercise the bug."
        )
        await ValidationService.persist_findings(db_session, document_id, validation_findings)

        with (
            patch(
                "app.services.due_diligence_service.AIService.generate_due_diligence_report",
                new=AsyncMock(return_value=_fake_report_with_no_red_flags()),
            ),
            patch(
                "app.services.due_diligence_service.RetrievalService.semantic_search",
                new=AsyncMock(return_value=[]),
            ),
        ):
            response = await DueDiligenceService.generate_report(db_session, document_id, actor_id, top_k=5)

        red_flags_section = next(s for s in response.sections if s.title == "Red Flags")

        # The model's own (buggy) text is preserved, not silently
        # replaced -- but the contradiction is gone: the critical
        # finding is now unavoidably present in the same section.
        assert "No red flags were identified." in red_flags_section.content
        critical_finding_titles = [f.title for f in validation_findings if f.severity.value == "critical"]
        assert critical_finding_titles, "expected at least one critical finding title to check for"
        assert any(title in red_flags_section.content for title in critical_finding_titles)
