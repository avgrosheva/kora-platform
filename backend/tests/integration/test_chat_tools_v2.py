"""Tests for chat_v2's tool layer (Evidence Layer plan, Step 10, and the
chat-scope fix that followed it).

Covers:
- get_findings / get_qualitative_facts (Step 10) and the Bug B fix
  inside execute_get_missing_information, which had never been updated
  when documents.py's endpoints were fixed in Step 2 -- it still
  hardcoded company/market/team found sets to empty.
- The chat-scope fix: the `/chat` page has no document selector at all,
  so `document_id` is `None` on effectively every real request.
  `execute_get_missing_information`/`execute_get_findings`/
  `execute_get_qualitative_facts` previously returned "No document is
  in scope for this question" unconditionally in that case -- these
  tests prove they now fall back to an organization-wide answer
  instead, tagging every result with which document it came from.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.qualitative_fact import QualitativeFactCategory, QualitativeFactSeverityHint
from app.schemas.cited_extraction import CitedQualitativeFact
from app.services.chat_tools import (
    execute_get_findings,
    execute_get_missing_information,
    execute_get_qualitative_facts,
)
from app.services.document_analysis_service import DocumentAnalysisService

from tests.integration.test_marketgo_end_to_end import _cited, CitedBusinessAnalysisResult


def _business_analysis_with_facts():
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
                claim_text="Relies on a single payment processor.",
                severity_hint=QualitativeFactSeverityHint.HIGH,
                quote="MarketGo is an e-commerce marketplace.", page_number=2, confidence=0.75,
            ),
            CitedQualitativeFact(
                category=QualitativeFactCategory.OPPORTUNITY,
                claim_text="Expansion into adjacent international markets.",
                severity_hint=None,
                quote="MarketGo is an e-commerce marketplace.", page_number=2, confidence=0.7,
            ),
        ],
    )


async def _analyze_marketgo_with_citations(db_session, marketgo_document, integration_user):
    with patch(
        "app.services.document_analysis_service.AIService.generate_cited_business_analysis",
        new=AsyncMock(return_value=_business_analysis_with_facts()),
    ):
        await DocumentAnalysisService.analyze_document_with_citations(
            db_session, marketgo_document.id, integration_user.id
        )


@pytest.mark.asyncio(loop_scope="session")
class TestNoDocumentAndNoOrganizationDocuments:
    """When neither a specific document is selected NOR the organization
    has any completed document at all, tools must say so plainly --
    this is a genuinely different situation from "you forgot to pick a
    document" (which no longer exists as an error path for these three
    tools) and from "the organization has documents but this one
    question found nothing relevant"."""

    async def test_get_missing_information_with_no_documents_in_org(
        self, db_session, integration_org, integration_user
    ):
        summary, result = await execute_get_missing_information(
            db_session, integration_org.id, None, integration_user.id, {}
        )
        assert result == {"error": "no_processed_documents"}
        assert "No processed documents" in summary

    async def test_get_findings_with_no_documents_in_org(self, db_session, integration_org, integration_user):
        summary, result = await execute_get_findings(db_session, integration_org.id, None, integration_user.id, {})
        assert result == {"error": "no_processed_documents"}

    async def test_get_qualitative_facts_with_no_documents_in_org(
        self, db_session, integration_org, integration_user
    ):
        summary, result = await execute_get_qualitative_facts(
            db_session, integration_org.id, None, integration_user.id, {}
        )
        assert result == {"error": "no_processed_documents"}


@pytest.mark.asyncio(loop_scope="session")
class TestOrganizationWideFallback:
    """The chat-scope regression test: a question with no document
    selected, in an organization that DOES have a processed document
    with real findings, must return those findings -- not "no document
    is in scope for this question". This is the exact bug reported live
    against E_PayHarbor.pdf."""

    async def test_get_findings_falls_back_to_organization_wide(
        self, db_session, marketgo_document, integration_user
    ):
        await _analyze_marketgo_with_citations(db_session, marketgo_document, integration_user)

        summary, result = await execute_get_findings(
            db_session, marketgo_document.organization_id, None, integration_user.id, {}
        )

        assert "error" not in result
        assert len(result["findings"]) > 0
        assert all(f["document_id"] == str(marketgo_document.id) for f in result["findings"])
        assert all(f["document_name"] == marketgo_document.original_filename for f in result["findings"])
        assert "across 1 document" in summary

    async def test_get_qualitative_facts_falls_back_to_organization_wide(
        self, db_session, marketgo_document, integration_user
    ):
        await _analyze_marketgo_with_citations(db_session, marketgo_document, integration_user)

        _, result = await execute_get_qualitative_facts(
            db_session, marketgo_document.organization_id, None, integration_user.id, {}
        )

        assert len(result["facts"]) > 0
        assert all(f["document_id"] == str(marketgo_document.id) for f in result["facts"])

    async def test_get_missing_information_falls_back_to_organization_wide(
        self, db_session, marketgo_document, integration_user
    ):
        await _analyze_marketgo_with_citations(db_session, marketgo_document, integration_user)

        _, result = await execute_get_missing_information(
            db_session, marketgo_document.organization_id, None, integration_user.id, {}
        )

        assert "documents" in result  # org-wide shape, distinct from single-document's "by_category"
        assert len(result["documents"]) == 1
        assert result["documents"][0]["document_id"] == str(marketgo_document.id)

    async def test_explicit_document_id_is_unaffected_by_the_fallback(
        self, db_session, marketgo_document, integration_user
    ):
        """When a document IS explicitly selected, behavior and result
        shape must be identical to before this fix -- no document_id/
        document_name tagging noise, single-document shape."""
        await _analyze_marketgo_with_citations(db_session, marketgo_document, integration_user)

        _, result = await execute_get_findings(
            db_session, marketgo_document.organization_id, marketgo_document.id, integration_user.id, {}
        )
        assert len(result["findings"]) > 0
        assert all(f["document_id"] is None for f in result["findings"])


@pytest.mark.asyncio(loop_scope="session")
class TestChatToolsV2WithRealData:
    async def test_get_missing_information_reflects_populated_analysis(
        self, db_session, marketgo_document, integration_user
    ):
        """Bug B, fixed here: a company field that IS found must not be
        reported as missing by this tool."""
        await _analyze_marketgo_with_citations(db_session, marketgo_document, integration_user)

        _, result = await execute_get_missing_information(
            db_session, marketgo_document.organization_id, marketgo_document.id, integration_user.id, {}
        )
        company_category = next((c for c in result["by_category"] if c["category"] == "company"), None)
        # company_name, industry, business_model, summary were all
        # populated above -- none of them should show as missing.
        if company_category is not None:
            assert "company_name" not in company_category["missing"]
            assert "industry" not in company_category["missing"]

    async def test_get_findings_includes_type_labeled_results(
        self, db_session, marketgo_document, integration_user
    ):
        await _analyze_marketgo_with_citations(db_session, marketgo_document, integration_user)

        summary, result = await execute_get_findings(
            db_session, marketgo_document.organization_id, marketgo_document.id, integration_user.id, {}
        )
        types_present = {f["type"] for f in result["findings"]}
        assert "document_stated" in types_present
        assert "ai_inferred" in types_present
        # The opportunity claim (no severity_hint) must not appear here.
        assert not any(f["category"] == "opportunity" for f in result["findings"])
        assert "critical/high" in summary

    async def test_get_qualitative_facts_includes_opportunities_unlike_get_findings(
        self, db_session, marketgo_document, integration_user
    ):
        await _analyze_marketgo_with_citations(db_session, marketgo_document, integration_user)

        _, result = await execute_get_qualitative_facts(
            db_session, marketgo_document.organization_id, marketgo_document.id, integration_user.id, {}
        )
        categories_present = {f["category"] for f in result["facts"]}
        assert "opportunity" in categories_present
        assert "operational_dependency" in categories_present
