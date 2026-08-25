"""End-to-end test for FindingsService (Evidence Layer plan, Step 5).

Drives the real, database-backed pipeline: the validation engine
(unchanged, run for real against real FactPoints) plus the cited
business-analysis extraction (mocked only at the AI boundary) both
persist their own rows, and `FindingsService.get_findings` assembles
all three finding kinds from what's actually in the database -- proving
the facade works against real data, not just mocked service calls.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.qualitative_fact import QualitativeFactCategory, QualitativeFactSeverityHint
from app.schemas.cited_extraction import CitedQualitativeFact
from app.services.derived_metrics_service import FactPoint
from app.services.document_analysis_service import DocumentAnalysisService
from app.services.financial_facts_service import FinancialFactsService
from app.services.findings_service import FindingType, FindingsService
from app.services.validation_service import ValidationService, run_all_validations
from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P

from tests.integration.test_marketgo_end_to_end import _cited, CitedBusinessAnalysisResult


def _fake_business_analysis_with_qualitative_facts():
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
                claim_text="Relies on a single third-party payment processor for all transactions.",
                severity_hint=QualitativeFactSeverityHint.HIGH,
                quote="MarketGo is an e-commerce marketplace.",
                page_number=2, confidence=0.75,
            ),
            CitedQualitativeFact(
                category=QualitativeFactCategory.OPPORTUNITY,
                claim_text="Expansion into adjacent international markets.",
                severity_hint=None,
                quote="MarketGo is an e-commerce marketplace.",
                page_number=2, confidence=0.7,
            ),
        ],
    )


@pytest.mark.asyncio(loop_scope="session")
class TestFindingsServicePipeline:
    async def test_get_findings_combines_real_validation_and_qualitative_data(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        # Deterministic side: a hand-built fact set with a genuine
        # EBITDA > revenue inconsistency, run through the real,
        # unmodified validation engine.
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
        await ValidationService.persist_findings(db_session, document_id, validation_findings)

        # Qualitative side: cited extraction, mocked at the AI boundary only.
        with patch(
            "app.services.document_analysis_service.AIService.generate_cited_business_analysis",
            new=AsyncMock(return_value=_fake_business_analysis_with_qualitative_facts()),
        ):
            await DocumentAnalysisService.analyze_document_with_citations(db_session, document_id, actor_id)

        findings = await FindingsService.get_findings(db_session, document_id)
        types = [f.type for f in findings]

        # At least one real deterministic finding from the EBITDA>revenue check.
        assert FindingType.DETERMINISTIC in types
        assert any("EBITDA" in (f.title + (f.explanation or "")) for f in findings if f.type == FindingType.DETERMINISTIC)

        # The operational_dependency claim: one document-stated finding
        # (the claim itself) plus one ai_inferred finding (the
        # concentration-risk consequence Kora draws from it).
        document_stated = [f for f in findings if f.type == FindingType.DOCUMENT_STATED]
        inferred = [f for f in findings if f.type == FindingType.AI_INFERRED]
        assert len(document_stated) == 1
        assert document_stated[0].category == "operational_dependency"
        assert len(inferred) == 1
        assert "Kora-inferred" in inferred[0].title

        # The opportunity claim (severity_hint=None) must NOT appear as
        # a finding anywhere -- it's not a risk.
        assert not any(f.category == "opportunity" for f in findings)
        assert not any("international" in (f.evidence or "") for f in findings)
