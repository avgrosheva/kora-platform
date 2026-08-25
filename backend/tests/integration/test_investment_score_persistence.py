"""Integration test for Step 8 of the Evidence Layer plan.

Proves two things end-to-end against the real database:

1. `assessment_status` is computed from real coverage/confidence/
   dimension-count inputs and actually persisted (not just present on
   the in-memory `ScoringResult`).
2. `methodology_version` and `category_breakdown` -- which
   `ScoringResult` has always computed, but which the persistence code
   silently never wrote to the database or returned from the API before
   this step -- are now genuinely persisted and readable back after a
   fresh fetch, not just present on the object returned from the same
   call that created it.
"""

import pytest

from app.core.scoring_config import SCORING_METHODOLOGY_VERSION
from app.models.document_analysis import DocumentAnalysis
from app.models.financial_fact import FinancialValueType, PeriodType
from app.models.financial_metrics import FinancialMetrics
from app.models.qualitative_fact import (
    QualitativeFactCategory,
    QualitativeFactSeverityHint,
    QualitativeFactType,
)
from app.services.coverage_service import REQUIRED_FINANCIAL_METRICS
from app.services.financial_facts_service import FinancialFactsService
from app.services.investment_scoring_service import InvestmentScoringService
from app.services.qualitative_facts_service import QualitativeFactsService


@pytest.mark.asyncio(loop_scope="session")
class TestInvestmentScorePersistence:
    async def test_sufficient_evidence_score_persists_all_new_fields(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        analysis = DocumentAnalysis(
            document_id=document_id, company_name="MarketGo", industry="E-commerce",
            business_model="Marketplace", summary="Summary.", key_products=["Platform"],
            revenue_streams=["Fees"], customers=["Shoppers"], competitors=["Rival"], raw_json={},
        )
        db_session.add(analysis)

        fm = FinancialMetrics(
            document_id=document_id, currency="USD", revenue=1_000_000, arr=1_200_000, mrr=100_000,
            gross_margin=60, ebitda=100_000, burn_rate=50_000, runway_months=20, cash=1_000_000,
            customers=100, growth_rate=40, cac=100, ltv=500, valuation=10_000_000, confidence_score=0.9,
        )
        db_session.add(fm)
        await db_session.commit()

        # Full 10/10 required financial metrics found -> financial coverage = 1.0.
        await FinancialFactsService.replace_facts(db_session, document_id, [
            {"metric": metric, "value": 1.0, "period": "2025", "period_type": PeriodType.YEAR,
             "value_type": FinancialValueType.ACTUAL, "currency": "USD"}
            for metric in REQUIRED_FINANCIAL_METRICS
        ])

        # A market_risk qualitative fact -> matches the "market_risks"
        # checklist item, giving market coverage a nonzero value too.
        await QualitativeFactsService.replace_facts(db_session, document_id, [
            {"category": QualitativeFactCategory.MARKET_RISK, "claim_text": "Competitive market.",
             "fact_type": QualitativeFactType.DOCUMENT_STATED, "severity_hint": QualitativeFactSeverityHint.LOW,
             "confidence": 0.7},
        ])

        score = await InvestmentScoringService.calculate_score(db_session, document_id, actor_id)

        assert score.assessment_status == "sufficient_evidence"
        assert score.overall_score is not None
        assert score.methodology_version == SCORING_METHODOLOGY_VERSION
        assert score.category_breakdown is not None
        assert score.category_breakdown["financial_score"]["status"] == "assessed"

        # Re-fetch independently to prove this round-tripped through the
        # database, not just present on the in-memory return value.
        fetched = await InvestmentScoringService.get_score(db_session, document_id, actor_id)
        assert fetched.assessment_status == "sufficient_evidence"
        assert fetched.overall_score == score.overall_score
        assert fetched.methodology_version == SCORING_METHODOLOGY_VERSION
        assert fetched.category_breakdown is not None
        assert fetched.category_breakdown["market_score"]["status"] == "assessed"

    async def test_insufficient_evidence_persists_null_overall_score(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        # Only ARR -- one dimension, thin coverage. Must NOT produce a
        # confident-looking composite number.
        fm = FinancialMetrics(
            document_id=document_id, currency="USD", arr=12_000_000, revenue=None, mrr=None,
            gross_margin=None, ebitda=None, burn_rate=None, runway_months=None, cash=None,
            customers=None, growth_rate=None, cac=None, ltv=None, valuation=None, confidence_score=None,
        )
        db_session.add(fm)
        await db_session.commit()

        score = await InvestmentScoringService.calculate_score(db_session, document_id, actor_id)

        assert score.assessment_status == "insufficient_evidence"
        assert score.overall_score is None
        assert score.financial_score is not None  # the one assessed dimension is still shown

        fetched = await InvestmentScoringService.get_score(db_session, document_id, actor_id)
        assert fetched.assessment_status == "insufficient_evidence"
        assert fetched.overall_score is None
