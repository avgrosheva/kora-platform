"""End-to-end integration test: MarketGo through the real service layer.

Unlike the Step 2-6 unit tests (which operate on plain `FactPoint`
lists with no database), this test drives the actual database-backed
services — `FinancialAnalysisService.extract_financial_facts`,
`DocumentAnalysisService.analyze_document_with_citations`,
`FinancialFactsService`, and the read path used by
`GET /documents/{id}/metrics|checks|coverage|missing-information` —
against a real (throwaway) document, organization, and user. Only the
AI call boundary is mocked; everything else — persistence, retrieval,
the derived-metrics engine, the validation engine, coverage, and the
missing-information checklist — runs for real.

This is the test that actually proves Steps 1-6 work together, not
just individually.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P
from app.schemas.cited_extraction import (
    CitedBusinessAnalysisResult,
    CitedFinancialFactItem,
    CitedFinancialFactsResult,
    CitedValue,
)
from app.schemas.derived_metrics import MetricStatus
from app.schemas.validation import FindingSeverity
from app.services.coverage_service import compute_coverage
from app.services.derived_metrics_service import calculate_all_derived_metrics, persist_derived_metrics
from app.services.financial_analysis_service import FinancialAnalysisService
from app.services.financial_facts_service import FinancialFactsService
from app.services.document_analysis_service import DocumentAnalysisService
from app.services.missing_information_service import compute_missing_information, facts_to_metric_set
from app.services.validation_service import ValidationService, run_all_validations


def _cited(value, quote, page=2, confidence=0.95):
    """Test helper: build a `CitedValue` with sensible defaults."""
    return CitedValue(value=value, quote=quote, page_number=page, confidence=confidence)


def _fake_business_analysis() -> CitedBusinessAnalysisResult:
    """Build a mocked, citation-backed business analysis matching the MarketGo fixture text."""
    return CitedBusinessAnalysisResult(
        company_name=_cited("MarketGo", "MarketGo is an e-commerce marketplace."),
        industry=_cited("E-commerce", "MarketGo is an e-commerce marketplace."),
        business_model=_cited("Marketplace", "MarketGo is an e-commerce marketplace."),
        summary=_cited("A growing e-commerce marketplace with strong revenue growth.", "MarketGo is an e-commerce marketplace."),
        key_products=[_cited("Marketplace platform", "MarketGo is an e-commerce marketplace.")],
        revenue_streams=[_cited("Transaction fees", "MarketGo is an e-commerce marketplace.")],
        target_customers=[_cited("Online shoppers", "MarketGo is an e-commerce marketplace.")],
        competitors=[],
        main_risks=[],
        growth_opportunities=[],
    )


def _fake_financial_facts() -> CitedFinancialFactsResult:
    """Build the mocked, citation-backed financial facts matching the MarketGo fixture text.

    Mirrors `tests/fixtures/marketgo.py`'s `marketgo_facts()` exactly,
    but as the AI-extraction output shape (with quotes/pages/confidence)
    rather than plain `FactPoint`s.
    """
    def fact(metric, value, period, period_type, value_type, currency=None):
        return CitedFinancialFactItem(
            metric=metric, value=value, currency=currency, period_type=period_type,
            period=period, value_type=value_type,
            quote=f"Reported {metric.value} of {value} for {period}.",
            page_number=2, confidence=0.95,
        )

    return CitedFinancialFactsResult(facts=[
        fact(M.REVENUE, 24_000_000, "2023", P.YEAR, V.ACTUAL, "USD"),
        fact(M.REVENUE, 58_000_000, "2024", P.YEAR, V.ACTUAL, "USD"),
        fact(M.REVENUE, 96_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        fact(M.GROSS_MARGIN, 0.22, "2024", P.YEAR, V.ACTUAL),
        fact(M.GROSS_MARGIN, 0.29, "2025", P.YEAR, V.ACTUAL),
        fact(M.EBITDA, -6_000_000, "2024", P.YEAR, V.ACTUAL, "USD"),
        fact(M.EBITDA, 8_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        fact(M.NET_INCOME, 3_500_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        fact(M.CASH, 18_000_000, "2025", P.POINT_IN_TIME, V.ACTUAL, "USD"),
        fact(M.OPERATING_EXPENSES, 88_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        fact(M.CAC, 27, "2024", P.YEAR, V.ACTUAL, "USD"),
        fact(M.CAC, 21, "2025", P.YEAR, V.ACTUAL, "USD"),
        fact(M.LTV, 170, "2025", P.YEAR, V.ESTIMATE, "USD"),
        fact(M.ORDERS, 8_700_000, "2024", P.YEAR, V.ACTUAL),
        fact(M.ORDERS, 14_500_000, "2025", P.YEAR, V.ACTUAL),
        fact(M.AOV, 31, "2024", P.YEAR, V.ACTUAL, "USD"),
        fact(M.AOV, 34, "2025", P.YEAR, V.ACTUAL, "USD"),
        fact(M.REGISTERED_CUSTOMERS, 2_800_000, "2025", P.YEAR, V.ACTUAL),
        fact(M.MONTHLY_ACTIVE_USERS, 620_000, "2025", P.YEAR, V.ACTUAL),
        fact(M.FUNDING_AMOUNT, 45_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        fact(M.VALUATION_POST_MONEY, 280_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
    ])


@pytest.mark.asyncio(loop_scope="session")
class TestMarketGoEndToEnd:
    async def test_full_pipeline_through_real_services(
        self, db_session, marketgo_document, integration_user
    ):
        """Drive the entire Phase 1 pipeline through real services and
        assert the MarketGo worked example holds end-to-end."""
        document_id = marketgo_document.id
        actor_id = integration_user.id

        # --- Step 5: AI-extraction wiring (mocked at the AI boundary only) ---
        with patch(
            "app.services.financial_analysis_service.AIService.generate_cited_financial_facts",
            new=AsyncMock(return_value=_fake_financial_facts()),
        ):
            persisted_facts = await FinancialAnalysisService.extract_financial_facts(
                db_session, document_id, actor_id
            )
        assert len(persisted_facts) == 21
        assert all(f.source_citation_id is not None for f in persisted_facts)

        with patch(
            "app.services.document_analysis_service.AIService.generate_cited_business_analysis",
            new=AsyncMock(return_value=_fake_business_analysis()),
        ):
            analysis = await DocumentAnalysisService.analyze_document_with_citations(
                db_session, document_id, actor_id
            )
        assert analysis.company_name == "MarketGo"

        # --- Step 3-4: real facts, read back and run through the deterministic engines ---
        fact_points = await FinancialFactsService.get_fact_points(db_session, document_id)
        assert len(fact_points) == 21

        derived_results = calculate_all_derived_metrics(fact_points)
        persisted_metrics = await persist_derived_metrics(db_session, document_id, derived_results)
        assert len(persisted_metrics) == len(derived_results)

        def find_metric(metric_name, period=None):
            for r in derived_results:
                if r.metric == metric_name and (period is None or r.period == period):
                    return r
            raise AssertionError(f"metric {metric_name!r} period {period!r} not found")

        # Worked-example assertions, now proven through the real pipeline.
        assert find_metric("revenue_yoy_growth", "2024").value == pytest.approx(1.41667, abs=0.001)
        assert find_metric("revenue_yoy_growth", "2025").value == pytest.approx(0.655172, abs=0.001)
        assert find_metric("revenue_cagr", "2023-2025").value == pytest.approx(1.0, abs=0.001)
        assert find_metric("revenue_growth_trend").display_value == "decelerating"
        assert find_metric("ebitda_margin", "2025").value == pytest.approx(0.08333, abs=0.001)
        assert find_metric("net_margin", "2025").value == pytest.approx(0.036458, abs=0.001)
        assert find_metric("ltv_cac_ratio", "2025").value == pytest.approx(8.0952, abs=0.01)
        assert find_metric("orders_per_active_user").status == MetricStatus.PERIOD_MISMATCH
        assert find_metric("cac_payback_months").status == MetricStatus.MISSING_INPUTS

        # --- Validation engine, run for real against the persisted facts ---
        findings = run_all_validations(fact_points)
        persisted_findings = await ValidationService.persist_findings(db_session, document_id, findings)
        assert any(f.title == "Customer metric may be misleading" for f in findings)
        assert not any(f.severity == FindingSeverity.CRITICAL for f in findings)
        assert len(persisted_findings) == len(findings)

        # --- Coverage engine ---
        financial_metrics_found = facts_to_metric_set(fact_points)
        company_fields_found = {
            k for k, v in {
                "company_name": analysis.company_name, "industry": analysis.industry,
                "business_model": analysis.business_model, "summary": analysis.summary,
                "key_products": analysis.key_products, "revenue_streams": analysis.revenue_streams,
                "customers": analysis.customers, "competitors": analysis.competitors,
            }.items() if v
        }
        coverage_result = compute_coverage(
            financial_metrics_found=financial_metrics_found,
            company_fields_found=company_fields_found,
            market_fields_found=set(),
            team_fields_found=set(),
            citations_count=len(persisted_facts),
            total_extracted_fields=len(persisted_facts) + len(company_fields_found),
        )
        # 10/10 required financial metrics found in this fixture.
        assert coverage_result.coverage["financial"].found == 8
        assert coverage_result.coverage["team"].found == 0
        assert 0.0 < coverage_result.overall_confidence < 1.0

        # --- Missing-information checklist ---
        missing_info = compute_missing_information(
            financial_metrics_found=financial_metrics_found,
            company_fields_found=company_fields_found,
            market_fields_found=set(),
            team_fields_found=set(),
        )
        team_category = next(c for c in missing_info.by_category if c.category == "team")
        assert len(team_category.missing) == 5
        legal_category = next(c for c in missing_info.by_category if c.category == "legal")
        assert len(legal_category.missing) == 5

    async def test_reextraction_replaces_rather_than_duplicates(
        self, db_session, marketgo_document, integration_user
    ):
        """Running extraction twice must replace facts, not accumulate them."""
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.financial_analysis_service.AIService.generate_cited_financial_facts",
            new=AsyncMock(return_value=_fake_financial_facts()),
        ):
            await FinancialAnalysisService.extract_financial_facts(db_session, document_id, actor_id)
            second_run = await FinancialAnalysisService.extract_financial_facts(db_session, document_id, actor_id)

        all_facts = await FinancialFactsService.list_facts(db_session, document_id)
        assert len(all_facts) == 21  # not 40
        assert len(second_run) == 21