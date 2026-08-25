"""Unit tests for the flat-to-financial_facts unit normalization fix.

Regression coverage for the gross_margin unit mismatch: the flat
extraction schema states percentages as plain numbers (71 for 71%),
but `financial_facts` has an established fraction convention (0.71 for
71%) that both `validation_service.py`'s plausible-range check and
`derived_metrics_service.py`'s "Revenue x Gross Margin" gross-profit
estimate depend on. Found live on a real document after Step 3 shipped
the flat-to-financial_facts mirror without this conversion.
"""

from app.models.financial_fact import FinancialMetricType as M
from app.schemas.financial_metrics import FinancialMetricsCreate
from app.services.financial_analysis_service import (
    _facts_from_flat_metrics,
    _normalize_flat_value,
)


def _metrics_data(**overrides) -> FinancialMetricsCreate:
    defaults = dict(
        currency="USD", revenue=42_000_000, arr=None, mrr=None, gross_margin=71.0,
        ebitda=4_200_000, burn_rate=None, runway_months=None, cash=None, customers=None,
        growth_rate=None, cac=None, ltv=None, valuation=None, confidence_score=0.5,
    )
    defaults.update(overrides)
    return FinancialMetricsCreate(**defaults)


class TestNormalizeFlatValue:
    def test_gross_margin_is_converted_to_a_fraction(self):
        assert _normalize_flat_value("gross_margin", 71.0) == 0.71

    def test_gross_margin_of_zero_stays_zero(self):
        assert _normalize_flat_value("gross_margin", 0.0) == 0.0

    def test_dollar_amount_fields_are_unchanged(self):
        assert _normalize_flat_value("revenue", 42_000_000) == 42_000_000
        assert _normalize_flat_value("ebitda", 4_200_000) == 4_200_000
        assert _normalize_flat_value("cash", 18_000_000) == 18_000_000
        assert _normalize_flat_value("cac", 21) == 21
        assert _normalize_flat_value("ltv", 170) == 170
        assert _normalize_flat_value("burn_rate", 500_000) == 500_000


class TestFactsFromFlatMetricsUnitConversion:
    def test_gross_margin_fact_is_a_fraction_not_a_raw_percentage(self):
        """The exact bug: gross_margin=71.0 (71%, flat convention) must
        become a financial_facts row with value=0.71, not 71.0 -- 71.0
        would trip validation_service.py's plausible-range check
        (expects -1.0..1.5) and corrupt derived_metrics_service.py's
        "Revenue x Gross Margin" gross-profit estimate by 100x."""
        facts = _facts_from_flat_metrics(_metrics_data(gross_margin=71.0))
        gross_margin_fact = next(f for f in facts if f["metric"] == M.GROSS_MARGIN)
        assert gross_margin_fact["value"] == 0.71

    def test_other_mapped_fields_are_not_converted(self):
        facts = _facts_from_flat_metrics(_metrics_data(gross_margin=71.0))
        by_metric = {f["metric"]: f["value"] for f in facts}
        assert by_metric[M.REVENUE] == 42_000_000
        assert by_metric[M.EBITDA] == 4_200_000

    def test_realistic_high_margin_stays_within_plausible_range_as_a_fraction(self):
        """71% and even 99% margins are real (e.g. software gross
        margins) -- converted correctly, they must land well within
        validation_service.py's -1.0..1.5 plausible range."""
        facts = _facts_from_flat_metrics(_metrics_data(gross_margin=99.0))
        gross_margin_fact = next(f for f in facts if f["metric"] == M.GROSS_MARGIN)
        assert -1.0 <= gross_margin_fact["value"] <= 1.5
