"""Regression test for a real crash in `GET /documents/{id}/metrics`.

`DerivedMetricRead.id`/`.document_id` were typed `str`, but
`DerivedMetric` (the ORM row) stores both as `uuid.UUID` columns
(`Mapped[uuid.UUID]`). Pydantic v2 does not coerce a `UUID` instance
into a `str` field, so `get_document_metrics`'s
`DerivedMetricRead.model_validate(row)` raised `pydantic.ValidationError`
for every document that had at least one derived metric -- i.e. any
document that had gone through financial-facts extraction at all. This
is why it went unnoticed: every existing test for this data (coverage,
checks, derived-metrics engine itself) called the service layer
directly (`calculate_all_derived_metrics`, `persist_derived_metrics`,
`FinancialFactsService`), never the `get_document_metrics` endpoint
function that does the ORM-row-to-`DerivedMetricRead` conversion.

Per `ValidationFindingRead` (which already gets this right for the
`/checks` endpoint), the fix types `id`/`document_id` as `uuid.UUID`.
This test calls the endpoint FUNCTION ITSELF (`get_document_metrics`,
the same object FastAPI routes `GET /documents/{id}/metrics` to) rather
than the service layer underneath it, so a regression here -- in the
ORM-row -> response-model conversion specifically -- fails again even
if every service-layer test still passes.
"""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.api.v1.documents import get_document_metrics
from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P
from app.schemas.cited_extraction import CitedFinancialFactItem, CitedFinancialFactsResult
from app.services.financial_analysis_service import FinancialAnalysisService


def _cited_facts_with_a_calculable_metric() -> CitedFinancialFactsResult:
    """Two years of revenue -- enough for the derived-metrics engine to
    actually produce a CALCULATED row (YoY growth), not just an empty
    list, so this test exercises real `DerivedMetricRead` rows."""
    return CitedFinancialFactsResult(facts=[
        CitedFinancialFactItem(
            metric=M.REVENUE, value=58_000_000, currency="USD", period_type=P.YEAR,
            period="2024", value_type=V.ACTUAL,
            quote="Revenue of $58M in 2024.", page_number=2, confidence=0.95,
        ),
        CitedFinancialFactItem(
            metric=M.REVENUE, value=96_000_000, currency="USD", period_type=P.YEAR,
            period="2025", value_type=V.ACTUAL,
            quote="Revenue of $96M in 2025.", page_number=2, confidence=0.95,
        ),
    ])


@pytest.mark.asyncio(loop_scope="session")
class TestMetricsEndpointDerivedMetricIdTypes:
    async def test_get_document_metrics_does_not_crash_with_derived_rows(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.financial_analysis_service.AIService.generate_cited_financial_facts",
            new=AsyncMock(return_value=_cited_facts_with_a_calculable_metric()),
        ):
            await FinancialAnalysisService.extract_financial_facts(db_session, document_id, actor_id)

        # This is the exact call FastAPI makes for GET /documents/{id}/metrics.
        # Before the fix, this raised pydantic.ValidationError inside
        # DerivedMetricRead.model_validate(row).
        response = await get_document_metrics(document_id, db_session, integration_user)

        assert len(response.derived_metrics) > 0
        calculated = [row for row in response.derived_metrics if row.status == "calculated"]
        assert calculated, "expected at least one CALCULATED derived metric (revenue YoY growth)"

    async def test_derived_metric_id_and_document_id_are_uuids_that_serialize_to_strings(
        self, db_session, marketgo_document, integration_user
    ):
        """Guards the exact regression: `id`/`document_id` must be real
        `uuid.UUID` values on the model (matching the ORM column type,
        same as `ValidationFindingRead`), while still serializing to
        plain strings in the JSON response FastAPI actually sends."""
        document_id = marketgo_document.id
        actor_id = integration_user.id

        with patch(
            "app.services.financial_analysis_service.AIService.generate_cited_financial_facts",
            new=AsyncMock(return_value=_cited_facts_with_a_calculable_metric()),
        ):
            await FinancialAnalysisService.extract_financial_facts(db_session, document_id, actor_id)

        response = await get_document_metrics(document_id, db_session, integration_user)
        row = response.derived_metrics[0]

        assert isinstance(row.id, UUID)
        assert isinstance(row.document_id, UUID)
        assert row.document_id == document_id

        json_shape = row.model_dump(mode="json")
        assert isinstance(json_shape["id"], str)
        assert isinstance(json_shape["document_id"], str)
        assert json_shape["document_id"] == str(document_id)
