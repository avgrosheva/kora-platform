"""Integration test for Evidence Layer Step 9's founder-question rewrite.

Before this fix, `_build_founder_questions` only ever asked questions
from a fixed 6-entry template dict keyed by missing-field name (e.g.
generic "What is customer retention over time?") -- it never referenced
any value actually found in the document. This test drives the real
cited-extraction pipeline with a customer-concentration claim and
asserts the resulting founder question quotes that specific claim, not
a placeholder.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.missing_information_item import MissingInformationItem
from app.models.qualitative_fact import QualitativeFactCategory, QualitativeFactSeverityHint
from app.schemas.cited_extraction import CitedQualitativeFact
from app.services.document_analysis_service import DocumentAnalysisService
from app.services.due_diligence_v2_service import _build_founder_questions

from tests.integration.test_marketgo_end_to_end import _cited, CitedBusinessAnalysisResult


def _business_analysis_with_customer_concentration_claim():
    return CitedBusinessAnalysisResult(
        company_name=_cited("MarketGo", "MarketGo is an e-commerce marketplace."),
        industry=_cited("E-commerce", "MarketGo is an e-commerce marketplace."),
        business_model=_cited("Marketplace", "MarketGo is an e-commerce marketplace."),
        summary=_cited("A growing e-commerce marketplace.", "MarketGo is an e-commerce marketplace."),
        key_products=[], revenue_streams=[], target_customers=[], competitors=[],
        main_risks=[], growth_opportunities=[],
        qualitative_facts=[
            CitedQualitativeFact(
                category=QualitativeFactCategory.CUSTOMER_RISK,
                claim_text="The largest customer represents 42% of total revenue.",
                severity_hint=QualitativeFactSeverityHint.HIGH,
                quote="MarketGo is an e-commerce marketplace.",
                page_number=2, confidence=0.8,
            ),
        ],
    )


@pytest.mark.asyncio(loop_scope="session")
class TestFounderQuestionsReferenceActualEvidence:
    async def test_question_quotes_the_actual_percentage_not_a_generic_template(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.document_analysis_service.AIService.generate_cited_business_analysis",
            new=AsyncMock(return_value=_business_analysis_with_customer_concentration_claim()),
        ):
            await DocumentAnalysisService.analyze_document_with_citations(db_session, document_id, actor_id)

        questions = await _build_founder_questions(db_session, document_id)

        assert len(questions) >= 1
        matching = [q for q in questions if "42%" in q.question]
        assert matching, f"expected a question referencing the actual 42% figure, got: {questions}"
        assert matching[0].category == "customer_risk"
        assert matching[0].priority == "high"  # severity_hint was HIGH

    async def test_missing_field_uses_recommended_request_not_old_hardcoded_template(
        self, db_session, marketgo_document, integration_user
    ):
        """A genuinely missing checklist field (nothing extracted for
        it at all) must fall back to missing_information_service's
        recommended_request registry -- which explains WHY the request
        matters, not just the old 6-entry template dict this function
        used to hardcode ("Can you share the current cap table?", with
        no rationale)."""
        db_session.add(
            MissingInformationItem(
                document_id=marketgo_document.id, category="investment",
                field_name="cap_table", status="missing",
            )
        )
        await db_session.commit()

        questions = await _build_founder_questions(db_session, document_id=marketgo_document.id)

        cap_table_questions = [q for q in questions if q.category == "investment"]
        assert len(cap_table_questions) == 1
        # The recommended_request registry's text, not the old template's
        # bare "Can you share the current cap table?" with no rationale.
        assert "dilution" in cap_table_questions[0].question.lower()
        assert cap_table_questions[0].priority == "medium"
