"""Regression test for Evidence Layer Bug A.

Before this fix, there were two independent financial-extraction
pipelines writing to two different tables that nothing reconciled:

  - `POST /documents/{id}/financial-analysis` -> a single flat row in
    `financial_metrics` (revenue, arr, mrr, gross_margin, ebitda, ...).
  - `POST /documents/{id}/extract-financial-facts` -> many time-series
    rows in `financial_facts` (metric x period x value_type).

Coverage, derived metrics, and validation all read `financial_facts`
exclusively. A document that only ever went through the first pipeline
(which is the ONLY one actually wired to a button in the frontend today
-- `extract-financial-facts` has a ready `useExtractFinancialFacts` hook
but no UI entry point) would show fully-populated financial KPIs in the
Financials tab while Coverage reported "Financial 0/10" -- confirmed
against real dev-database data in the Step 0 diagnostic.

The fix: `FinancialAnalysisService.analyze_financial_metrics` now also
mirrors its mappable fields into `financial_facts` (uncited, since the
flat extraction has no quote), so the one existing user action produces
both outputs. This test proves that end-to-end: after calling
`/financial-analysis` alone, Coverage reflects the extracted metrics
with no second, manual step -- and that this doesn't clobber facts the
canonical, citation-backed pipeline already wrote for the same document.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.documents import get_document_coverage, get_document_missing_information
from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P
from app.schemas.cited_extraction import CitedFinancialFactItem, CitedFinancialFactsResult
from app.services.ai_service import AIAnalysisResult, FinancialExtractionResult
from app.services.document_analysis_service import DocumentAnalysisService
from app.services.financial_analysis_service import FinancialAnalysisService
from app.services.financial_facts_service import FinancialFactsService
from app.services.validation_service import ValidationService, run_all_validations


def _fake_business_analysis() -> AIAnalysisResult:
    """A minimal business analysis, just enough to satisfy
    `analyze_financial_metrics`'s prerequisite that DocumentAnalysis exists.
    """
    return AIAnalysisResult(
        company_name="MarketGo",
        industry="E-commerce",
        business_model="Marketplace",
        summary="A growing e-commerce marketplace.",
        key_products=None,
        revenue_streams=None,
        target_customers=None,
        competitors=None,
        main_risks=None,
        growth_opportunities=None,
    )


def _fake_flat_extraction(**overrides) -> FinancialExtractionResult:
    defaults = dict(
        currency="USD",
        revenue=96_000_000,
        arr=None,
        mrr=None,
        gross_margin=29.0,
        ebitda=8_000_000,
        burn_rate=500_000,
        cash=18_000_000,
        customers=None,
        growth_rate=None,
        cac=21,
        ltv=170,
        valuation=None,
    )
    defaults.update(overrides)
    return FinancialExtractionResult(**defaults)


@pytest.mark.asyncio(loop_scope="session")
class TestFinancialPipelineUnification:
    async def test_financial_analysis_alone_makes_coverage_reflect_metrics(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.document_analysis_service.AIService.analyze_document_text",
            new=AsyncMock(return_value=_fake_business_analysis()),
        ):
            await DocumentAnalysisService.analyze_document(db_session, document_id, actor_id)

        with patch(
            "app.services.financial_analysis_service.AIService.extract_financial_metrics",
            new=AsyncMock(return_value=_fake_flat_extraction()),
        ):
            await FinancialAnalysisService.analyze_financial_metrics(db_session, document_id, actor_id)

        # The flat pipeline alone must have populated financial_facts --
        # this is Bug A. All 7 mappable fields were non-null above.
        facts = await FinancialFactsService.list_facts(db_session, document_id)
        assert len(facts) == 7
        assert all(f.source_citation_id is None for f in facts)
        assert all(f.period is None and f.period_type == P.UNKNOWN.value for f in facts)
        assert {f.metric for f in facts} == {
            M.REVENUE.value, M.GROSS_MARGIN.value, M.EBITDA.value,
            M.BURN_RATE.value, M.CASH.value, M.CAC.value, M.LTV.value,
        }

        # No second, manual step: Coverage (Step 2's EvidenceService path)
        # must reflect this immediately.
        coverage = await get_document_coverage(document_id, db_session, integration_user)
        assert coverage.coverage["financial"].found == 7
        assert coverage.coverage["financial"].required == 10

        # And it must agree with Missing-Information (Bug B invariant),
        # extended here to the financial category: the 3 metrics the flat
        # pipeline cannot produce (no 1:1 mapping) are the only ones
        # still reported missing.
        missing_info = await get_document_missing_information(document_id, db_session, integration_user)
        financial_missing = next(c for c in missing_info.by_category if c.category == "financial")
        assert set(financial_missing.missing) == {
            M.NET_INCOME.value, M.DEBT.value, M.FUNDING_AMOUNT.value,
        }

    async def test_rerun_replaces_flat_derived_facts_not_duplicates(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.document_analysis_service.AIService.analyze_document_text",
            new=AsyncMock(return_value=_fake_business_analysis()),
        ):
            await DocumentAnalysisService.analyze_document(db_session, document_id, actor_id)

        with patch(
            "app.services.financial_analysis_service.AIService.extract_financial_metrics",
            new=AsyncMock(return_value=_fake_flat_extraction()),
        ):
            await FinancialAnalysisService.analyze_financial_metrics(db_session, document_id, actor_id)

        # Re-run with cash now missing -- the stale cash fact must be
        # removed, not left behind as a duplicate/contradictory row.
        with patch(
            "app.services.financial_analysis_service.AIService.extract_financial_metrics",
            new=AsyncMock(return_value=_fake_flat_extraction(cash=None)),
        ):
            await FinancialAnalysisService.analyze_financial_metrics(db_session, document_id, actor_id)

        facts = await FinancialFactsService.list_facts(db_session, document_id)
        assert len(facts) == 6
        assert M.CASH.value not in {f.metric for f in facts}

    async def test_canonical_cited_facts_survive_a_flat_pipeline_rerun(
        self, db_session, marketgo_document, integration_user
    ):
        """The two pipelines must coexist: running the flat pipeline for
        a document that already has canonical, citation-backed facts for
        the same metric must not delete the canonical facts.
        """
        document_id = marketgo_document.id
        actor_id = integration_user.id

        cited_facts = CitedFinancialFactsResult(facts=[
            CitedFinancialFactItem(
                metric=M.REVENUE, value=24_000_000, currency="USD", period_type=P.YEAR,
                period="2023", value_type=V.ACTUAL, quote="Revenue of $24M in 2023.",
                page_number=2, confidence=0.95,
            ),
            CitedFinancialFactItem(
                metric=M.REVENUE, value=96_000_000, currency="USD", period_type=P.YEAR,
                period="2025", value_type=V.ACTUAL, quote="Revenue of $96M in 2025.",
                page_number=2, confidence=0.95,
            ),
        ])
        with patch(
            "app.services.financial_analysis_service.AIService.generate_cited_financial_facts",
            new=AsyncMock(return_value=cited_facts),
        ):
            await FinancialAnalysisService.extract_financial_facts(db_session, document_id, actor_id)

        with patch(
            "app.services.document_analysis_service.AIService.analyze_document_text",
            new=AsyncMock(return_value=_fake_business_analysis()),
        ):
            await DocumentAnalysisService.analyze_document(db_session, document_id, actor_id)

        with patch(
            "app.services.financial_analysis_service.AIService.extract_financial_metrics",
            new=AsyncMock(return_value=_fake_flat_extraction()),
        ):
            await FinancialAnalysisService.analyze_financial_metrics(db_session, document_id, actor_id)

        facts = await FinancialFactsService.list_facts(db_session, document_id)
        cited_revenue = [f for f in facts if f.metric == M.REVENUE.value and f.source_citation_id is not None]
        uncited_revenue = [f for f in facts if f.metric == M.REVENUE.value and f.source_citation_id is None]

        # Both cited (2023, 2025) facts survived the flat pipeline run...
        assert {f.period for f in cited_revenue} == {"2023", "2025"}
        # ...and the flat pipeline's own uncited revenue fact was added
        # alongside them, not merged or deduped into one row.
        assert len(uncited_revenue) == 1
        assert uncited_revenue[0].period is None

    async def test_flat_gross_margin_does_not_trigger_a_false_plausible_range_finding(
        self, db_session, marketgo_document, integration_user
    ):
        """Regression test for the gross_margin unit-mismatch bug found
        live on E_PayHarbor.pdf: a document that went through ONLY
        /financial-analysis, with a perfectly normal gross_margin=71 (%),
        must not produce an "outside plausible range" validation finding.
        Before the fix, the flat pipeline mirrored 71.0 verbatim into
        financial_facts (fraction convention expected), which
        check_percentages_out_of_bounds read as 7100% and flagged.
        """
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.document_analysis_service.AIService.analyze_document_text",
            new=AsyncMock(return_value=_fake_business_analysis()),
        ):
            await DocumentAnalysisService.analyze_document(db_session, document_id, actor_id)

        with patch(
            "app.services.financial_analysis_service.AIService.extract_financial_metrics",
            new=AsyncMock(return_value=_fake_flat_extraction(gross_margin=71.0)),
        ):
            await FinancialAnalysisService.analyze_financial_metrics(db_session, document_id, actor_id)

        gross_margin_fact = next(
            f for f in await FinancialFactsService.list_facts(db_session, document_id)
            if f.metric == M.GROSS_MARGIN.value
        )
        assert gross_margin_fact.value == pytest.approx(0.71)

        fact_points = await FinancialFactsService.get_fact_points(db_session, document_id)
        findings = run_all_validations(fact_points)
        await ValidationService.persist_findings(db_session, document_id, findings)

        assert not any("gross_margin" in f.title for f in findings), (
            f"unexpected gross_margin finding(s): {[f.title for f in findings if 'gross_margin' in f.title]}"
        )
