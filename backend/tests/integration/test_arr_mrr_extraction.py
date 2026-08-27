"""End-to-end regression test: ARR/MRR no longer 502 the cited
financial-facts extraction pipeline.

Before this fix, `FinancialMetricType` had no ARR or MRR member, so an
AI response naming either as a fact's `metric` failed Pydantic
validation inside `_run_structured_completion` and surfaced as
`InvalidAIResponseError` -> HTTP 502 from `POST
/documents/{id}/extract-financial-facts` -- discarding every other,
validly-extracted fact in that same response too. This drives the real
service (`FinancialAnalysisService.extract_financial_facts`, only the
AI call boundary mocked) end-to-end with an AI response that names both
ARR and MRR, exactly as observed live, and confirms it persists cleanly
and flows through to `/metrics` and `/checks` with no error.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.documents import get_document_checks
from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P
from app.schemas.cited_extraction import CitedFinancialFactItem, CitedFinancialFactsResult
from app.services.derived_metrics_service import calculate_all_derived_metrics
from app.services.financial_analysis_service import FinancialAnalysisService
from app.services.financial_facts_service import FinancialFactsService


def _cited_facts_with_arr_and_mrr() -> CitedFinancialFactsResult:
    return CitedFinancialFactsResult(facts=[
        CitedFinancialFactItem(
            metric=M.ARR, value=12_000_000, currency="USD", period_type=P.POINT_IN_TIME,
            period="2025-06-30", value_type=V.ACTUAL,
            quote="As of June 30, 2025, ARR was $12M.", page_number=3, confidence=0.92,
        ),
        CitedFinancialFactItem(
            metric=M.MRR, value=1_000_000, currency="USD", period_type=P.MONTH,
            period="2025-06", value_type=V.ACTUAL,
            quote="MRR for June 2025 was $1M.", page_number=3, confidence=0.92,
        ),
        CitedFinancialFactItem(
            metric=M.REVENUE, value=11_500_000, currency="USD", period_type=P.YEAR,
            period="2024", value_type=V.ACTUAL,
            quote="Revenue of $11.5M in 2024.", page_number=2, confidence=0.95,
        ),
    ])


@pytest.mark.asyncio(loop_scope="session")
class TestArrMrrExtractionNoLongerFails:
    async def test_extraction_persists_arr_and_mrr_facts(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.financial_analysis_service.AIService.generate_cited_financial_facts",
            new=AsyncMock(return_value=_cited_facts_with_arr_and_mrr()),
        ):
            persisted = await FinancialAnalysisService.extract_financial_facts(
                db_session, document_id, actor_id
            )

        assert len(persisted) == 3
        by_metric = {f.metric: f for f in persisted}
        assert by_metric[M.ARR.value].value == 12_000_000
        assert by_metric[M.MRR.value].value == 1_000_000
        assert all(f.source_citation_id is not None for f in persisted)

    async def test_arr_and_mrr_flow_through_fact_points_and_checks(
        self, db_session, marketgo_document, integration_user
    ):
        """Not just persisted -- readable through the same read paths the
        UI's Metrics and Checks tabs use, with no crash from the new
        metric values."""
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.financial_analysis_service.AIService.generate_cited_financial_facts",
            new=AsyncMock(return_value=_cited_facts_with_arr_and_mrr()),
        ):
            await FinancialAnalysisService.extract_financial_facts(db_session, document_id, actor_id)

        # FinancialFactsService.get_fact_points converts every stored
        # metric string back to FinancialMetricType(...), which previously
        # would have been unreachable for "arr"/"mrr" since they could
        # never have been persisted in the first place.
        fact_points = await FinancialFactsService.get_fact_points(db_session, document_id)
        assert {f.metric for f in fact_points} == {M.ARR, M.MRR, M.REVENUE}

        # calculate_all_derived_metrics (the pure engine behind /metrics)
        # must not choke on ARR/MRR facts either.
        derived = calculate_all_derived_metrics(fact_points)
        assert isinstance(derived, list)

        checks = await get_document_checks(document_id, db_session, integration_user)
        assert checks is not None

    async def test_rerun_replaces_arr_mrr_facts_not_duplicates(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.financial_analysis_service.AIService.generate_cited_financial_facts",
            new=AsyncMock(return_value=_cited_facts_with_arr_and_mrr()),
        ):
            await FinancialAnalysisService.extract_financial_facts(db_session, document_id, actor_id)
            await FinancialAnalysisService.extract_financial_facts(db_session, document_id, actor_id)

        facts = await FinancialFactsService.list_facts(db_session, document_id)
        arr_facts = [f for f in facts if f.metric == M.ARR.value]
        mrr_facts = [f for f in facts if f.metric == M.MRR.value]
        assert len(arr_facts) == 1
        assert len(mrr_facts) == 1
