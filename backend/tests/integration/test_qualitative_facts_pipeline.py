"""End-to-end test for Evidence Layer Step 4 (qualitative_facts).

Drives the real, database-backed pipeline: the cited business-analysis
extraction (mocked only at the AI boundary) -> `QualitativeFact`
persistence with citations -> `EvidenceService` -> `GET .../coverage`.
Proves three things the plan called for:

1. The extended cited prompt's output persists as `QualitativeFact` rows,
   each with its own citation (unlike the flat financial pipeline, a
   qualitative fact always has a quote to cite).
2. Re-running extraction replaces rather than duplicates (same
   replace-on-rerun semantics as `financial_facts`).
3. `EvidenceService`/Coverage see real signal in the "team" and "market"
   categories for the first time -- with the deliberate asymmetry from
   `_field_name_for_qualitative_fact` holding: a market_risk claim moves
   Coverage's market count (it matches the "market_risks" checklist item
   exactly), a team_risk claim does NOT move Coverage's team count (it
   doesn't match any of the 5 specific REQUIRED_TEAM_FIELDS names) but
   IS visible via EvidenceService.get_evidence(category="team") -- and
   found never exceeds required either way (coverage_service.py's
   found-intersected-with-required fix, generalized in this step from
   the financial-only fix in Step 3).
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.documents import get_document_coverage
from app.models.qualitative_fact import QualitativeFactCategory, QualitativeFactSeverityHint
from app.schemas.cited_extraction import CitedQualitativeFact, CitedValue
from app.services.document_analysis_service import DocumentAnalysisService
from app.services.evidence_service import EvidenceService
from app.services.qualitative_facts_service import QualitativeFactsService

from tests.integration.test_marketgo_end_to_end import _cited, CitedBusinessAnalysisResult


def _fake_business_analysis_with_qualitative_facts(qualitative_facts):
    return CitedBusinessAnalysisResult(
        company_name=_cited("MarketGo", "MarketGo is an e-commerce marketplace."),
        industry=_cited("E-commerce", "MarketGo is an e-commerce marketplace."),
        business_model=_cited("Marketplace", "MarketGo is an e-commerce marketplace."),
        summary=_cited("A growing e-commerce marketplace.", "MarketGo is an e-commerce marketplace."),
        key_products=[],
        revenue_streams=[],
        target_customers=[],
        competitors=[],
        main_risks=[],
        growth_opportunities=[],
        qualitative_facts=qualitative_facts,
    )


def _team_and_market_facts():
    return [
        CitedQualitativeFact(
            category=QualitativeFactCategory.TEAM_RISK,
            claim_text="Key-person dependency on the founding CEO for major customer relationships.",
            severity_hint=QualitativeFactSeverityHint.MEDIUM,
            quote="MarketGo is an e-commerce marketplace.",
            page_number=2,
            confidence=0.7,
        ),
        CitedQualitativeFact(
            category=QualitativeFactCategory.MARKET_RISK,
            claim_text="Highly competitive marketplace segment with low seller switching costs.",
            severity_hint=QualitativeFactSeverityHint.LOW,
            quote="MarketGo is an e-commerce marketplace.",
            page_number=2,
            confidence=0.6,
        ),
    ]


@pytest.mark.asyncio(loop_scope="session")
class TestQualitativeFactsPipeline:
    async def test_cited_extraction_persists_qualitative_facts_with_citations(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.document_analysis_service.AIService.generate_cited_business_analysis",
            new=AsyncMock(return_value=_fake_business_analysis_with_qualitative_facts(_team_and_market_facts())),
        ):
            await DocumentAnalysisService.analyze_document_with_citations(db_session, document_id, actor_id)

        facts = await QualitativeFactsService.list_facts(db_session, document_id)
        assert len(facts) == 2
        assert all(f.source_citation_id is not None for f in facts)
        assert all(f.fact_type == "document_stated" for f in facts)

        team_fact = next(f for f in facts if f.category == "team_risk")
        market_fact = next(f for f in facts if f.category == "market_risk")
        assert team_fact.severity_hint == "medium"
        assert market_fact.severity_hint == "low"
        assert market_fact.confidence == 0.6

    async def test_rerun_replaces_rather_than_duplicates(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.document_analysis_service.AIService.generate_cited_business_analysis",
            new=AsyncMock(return_value=_fake_business_analysis_with_qualitative_facts(_team_and_market_facts())),
        ):
            await DocumentAnalysisService.analyze_document_with_citations(db_session, document_id, actor_id)
            await DocumentAnalysisService.analyze_document_with_citations(db_session, document_id, actor_id)

        facts = await QualitativeFactsService.list_facts(db_session, document_id)
        assert len(facts) == 2  # not 4

    async def test_evidence_service_and_coverage_reflect_qualitative_facts(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.document_analysis_service.AIService.generate_cited_business_analysis",
            new=AsyncMock(return_value=_fake_business_analysis_with_qualitative_facts(_team_and_market_facts())),
        ):
            await DocumentAnalysisService.analyze_document_with_citations(db_session, document_id, actor_id)

        # EvidenceService: both categories now carry real content -- true
        # for the first time for "team", since no other pipeline has ever
        # produced team-scoped evidence.
        team_evidence = await EvidenceService.get_evidence(db_session, document_id, category="team")
        market_evidence = await EvidenceService.get_evidence(db_session, document_id, category="market")
        assert len(team_evidence) == 1
        assert len(market_evidence) == 1
        assert market_evidence[0].field_name == "market_risks"

        # Coverage: market_risk matches the "market_risks" checklist item
        # exactly -> found=1. team_risk does NOT match any of the 5
        # specific REQUIRED_TEAM_FIELDS names -> found stays 0. This is
        # the deliberate asymmetry documented in
        # _field_name_for_qualitative_fact, not an oversight.
        coverage = await get_document_coverage(document_id, db_session, integration_user)
        assert coverage.coverage["market"].found == 1
        assert coverage.coverage["team"].found == 0
        # found must never exceed required, even with extra qualitative
        # evidence present in the same categories (the generalized
        # coverage_service.py intersection fix).
        assert coverage.coverage["market"].found <= coverage.coverage["market"].required
        assert coverage.coverage["team"].found <= coverage.coverage["team"].required
