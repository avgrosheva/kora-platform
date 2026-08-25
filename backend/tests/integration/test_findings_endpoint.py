"""Integration test for GET /documents/{id}/findings (Evidence Layer
plan, Step 7's backend prerequisite: the Checks tab can't distinguish
"no deterministic inconsistencies" from "no diligence risks identified"
without a surface for the fuller findings set FindingsService already
assembles).
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.documents import get_document_findings
from app.models.qualitative_fact import QualitativeFactCategory, QualitativeFactSeverityHint
from app.schemas.cited_extraction import CitedQualitativeFact
from app.services.document_analysis_service import DocumentAnalysisService

from tests.integration.test_marketgo_end_to_end import _cited, CitedBusinessAnalysisResult


def _business_analysis_with_operational_dependency():
    return CitedBusinessAnalysisResult(
        company_name=_cited("MarketGo", "MarketGo is an e-commerce marketplace."),
        industry=_cited("E-commerce", "MarketGo is an e-commerce marketplace."),
        business_model=_cited("Marketplace", "MarketGo is an e-commerce marketplace."),
        summary=_cited("A growing e-commerce marketplace.", "MarketGo is an e-commerce marketplace."),
        key_products=[], revenue_streams=[], target_customers=[], competitors=[],
        main_risks=[], growth_opportunities=[],
        qualitative_facts=[
            CitedQualitativeFact(
                category=QualitativeFactCategory.OPERATIONAL_DEPENDENCY,
                claim_text="Relies on a single third-party payment processor.",
                severity_hint=QualitativeFactSeverityHint.HIGH,
                quote="MarketGo is an e-commerce marketplace.",
                page_number=2, confidence=0.75,
            ),
        ],
    )


@pytest.mark.asyncio(loop_scope="session")
class TestGetDocumentFindingsEndpoint:
    async def test_returns_document_stated_and_inferred_findings_with_correct_counts(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.document_analysis_service.AIService.generate_cited_business_analysis",
            new=AsyncMock(return_value=_business_analysis_with_operational_dependency()),
        ):
            await DocumentAnalysisService.analyze_document_with_citations(db_session, document_id, actor_id)

        response = await get_document_findings(document_id, db_session, integration_user)

        assert response.document_id == document_id
        assert len(response.findings) == 2  # 1 document_stated + 1 ai_inferred
        assert response.document_stated_count == 1
        assert response.ai_inferred_count == 1
        assert response.deterministic_count == 0
        assert response.high_count == 2  # both the claim and its inferred consequence are "high"

        inferred = next(f for f in response.findings if f.type.value == "ai_inferred")
        assert "Kora-inferred" in inferred.title
        assert inferred.implication is not None

    async def test_no_findings_at_all_returns_empty_list_with_zero_counts(
        self, db_session, marketgo_document, integration_user
    ):
        response = await get_document_findings(marketgo_document.id, db_session, integration_user)
        assert response.findings == []
        assert response.critical_count == 0
        assert response.deterministic_count == 0
