"""Regression tests for the ARR/MRR FinancialMetricType gap.

Before this fix, `FinancialMetricType` had no ARR or MRR member. The
cited financial-facts extraction schema (`CitedFinancialFactItem.metric:
FinancialMetricType`) is strict (Pydantic raises `ValidationError` on an
unrecognized enum value), and `_run_structured_completion` in
`ai_service.py` converts any `ValidationError` from parsing the AI's raw
JSON into `InvalidAIResponseError`, which the `/extract-financial-facts`
endpoint maps to a 502 -- discarding every other, validly-extracted fact
in that same response, not just the ARR/MRR one. This was observed live
on real documents ("arr" is a natural label for a document's own
wording) and documented as a known gap in `ai_service.py` and
`financial_analysis_service.py` before this fix.

These tests exercise the exact mechanism that broke: constructing
`CitedFinancialFactsResult`/`CitedFinancialFactItem` from a raw dict
shaped like the AI's parsed JSON response (mirroring what
`_run_structured_completion` does with `response_model(**parsed)`).
"""

import pytest
from pydantic import ValidationError

from app.models.financial_fact import FinancialMetricType, FinancialValueType, PeriodType
from app.schemas.cited_extraction import CitedFinancialFactItem, CitedFinancialFactsResult


class TestFinancialMetricTypeHasArrAndMrr:
    def test_arr_and_mrr_are_valid_members(self):
        assert FinancialMetricType("arr") == FinancialMetricType.ARR
        assert FinancialMetricType("mrr") == FinancialMetricType.MRR

    def test_arr_and_mrr_are_distinct_from_revenue(self):
        assert FinancialMetricType.ARR != FinancialMetricType.REVENUE
        assert FinancialMetricType.MRR != FinancialMetricType.REVENUE


class TestCitedFinancialFactItemAcceptsArrAndMrr:
    """The exact regression: a raw AI JSON payload naming "arr"/"mrr" as
    the metric must validate successfully now, where it previously
    raised `pydantic.ValidationError` (-> `InvalidAIResponseError` ->
    HTTP 502)."""

    def _raw_fact(self, metric: str, value: float = 12_000_000.0, period: str = "2025") -> dict:
        return {
            "metric": metric,
            "value": value,
            "currency": "USD",
            "period_type": "point_in_time",
            "period": period,
            "value_type": "actual",
            "quote": f"{metric.upper()} of ${value:,.0f} as of {period}.",
            "page_number": 3,
            "confidence": 0.9,
        }

    def test_arr_fact_item_parses_from_raw_ai_json_shape(self):
        item = CitedFinancialFactItem(**self._raw_fact("arr"))
        assert item.metric == FinancialMetricType.ARR

    def test_mrr_fact_item_parses_from_raw_ai_json_shape(self):
        item = CitedFinancialFactItem(**self._raw_fact("mrr"))
        assert item.metric == FinancialMetricType.MRR

    def test_full_ai_response_with_arr_and_mrr_alongside_other_facts_parses(self):
        """The real failure mode: one bad metric name previously discarded
        the whole response, including every other valid fact in it."""
        raw_response = {
            "facts": [
                self._raw_fact("arr", 12_000_000.0, "2025"),
                self._raw_fact("mrr", 1_000_000.0, "2025-06"),
                {
                    "metric": "revenue", "value": 11_500_000.0, "currency": "USD",
                    "period_type": "year", "period": "2024", "value_type": "actual",
                    "quote": "Revenue of $11.5M in 2024.", "page_number": 2, "confidence": 0.95,
                },
            ]
        }
        result = CitedFinancialFactsResult(**raw_response)
        assert [f.metric for f in result.facts] == [
            FinancialMetricType.ARR, FinancialMetricType.MRR, FinancialMetricType.REVENUE,
        ]

    def test_still_rejects_a_genuinely_unknown_metric_name(self):
        """The fix adds legitimate members, not a validation bypass -- an
        actually-invalid metric name must still fail loudly."""
        with pytest.raises(ValidationError):
            CitedFinancialFactItem(**self._raw_fact("not_a_real_metric"))

    def test_arr_and_mrr_round_trip_through_the_orm_dict_shape(self):
        """The shape `FinancialFactsService.replace_facts` persists must
        also accept ARR/MRR values without needing special-casing."""
        item = CitedFinancialFactItem(**self._raw_fact("arr"))
        fact_dict = {
            "metric": item.metric, "value": item.value, "currency": item.currency,
            "period_type": item.period_type, "period": item.period,
            "value_type": item.value_type, "source_citation_id": None,
        }
        assert fact_dict["metric"].value == "arr"
        assert fact_dict["period_type"] == PeriodType.POINT_IN_TIME
        assert fact_dict["value_type"] == FinancialValueType.ACTUAL
