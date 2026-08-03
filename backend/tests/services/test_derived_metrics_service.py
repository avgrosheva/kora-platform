"""Unit tests for the deterministic derived-metrics engine.

Covers every formula against the MarketGo fixture (matching the
spec's worked example), plus explicit missing-input, period-mismatch,
and edge-case behavior. No database, no AI, no network — every test
runs in-process against plain `FactPoint` literals.
"""

import pytest

from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P
from app.schemas.derived_metrics import MetricStatus
from app.services.derived_metrics_service import (
    FactPoint,
    calculate_all_derived_metrics,
    calculate_growth_metrics,
    calculate_profitability_metrics,
    calculate_unit_economics_metrics,
    calculate_valuation_metrics,
)
from tests.fixtures.marketgo import marketgo_facts


def _find(results, metric: str, period: str | None = None):
    """Test helper: find the first result matching a metric (and period)."""
    for r in results:
        if r.metric == metric and (period is None or r.period == period):
            return r
    raise AssertionError(f"No result found for metric={metric!r} period={period!r}")


class TestGrowthMetrics:
    def test_revenue_yoy_growth_2024(self):
        results = calculate_growth_metrics(marketgo_facts())
        result = _find(results, "revenue_yoy_growth", "2024")
        assert result.status == MetricStatus.CALCULATED
        assert result.value == pytest.approx(1.41667, abs=0.001)
        assert result.display_value == "141.7%"

    def test_revenue_yoy_growth_2025(self):
        results = calculate_growth_metrics(marketgo_facts())
        result = _find(results, "revenue_yoy_growth", "2025")
        assert result.status == MetricStatus.CALCULATED
        assert result.value == pytest.approx(0.655172, abs=0.001)
        assert result.display_value == "65.5%"

    def test_revenue_cagr_2023_2025(self):
        results = calculate_growth_metrics(marketgo_facts())
        result = _find(results, "revenue_cagr", "2023-2025")
        assert result.status == MetricStatus.CALCULATED
        assert result.value == pytest.approx(1.0, abs=0.001)
        assert result.display_value == "100.0%"

    def test_revenue_growth_is_decelerating(self):
        results = calculate_growth_metrics(marketgo_facts())
        result = _find(results, "revenue_growth_trend")
        assert result.status == MetricStatus.CALCULATED
        assert result.display_value == "decelerating"

    def test_orders_yoy_growth(self):
        results = calculate_growth_metrics(marketgo_facts())
        result = _find(results, "orders_yoy_growth", "2025")
        assert result.value == pytest.approx(0.6667, abs=0.001)

    def test_aov_yoy_growth(self):
        results = calculate_growth_metrics(marketgo_facts())
        result = _find(results, "aov_yoy_growth", "2025")
        assert result.value == pytest.approx(0.09677, abs=0.001)

    def test_missing_inputs_when_fewer_than_two_years(self):
        facts = [FactPoint(M.REVENUE, 100.0, "2025", P.YEAR, V.ACTUAL)]
        results = calculate_growth_metrics(facts)
        result = _find(results, "revenue_yoy_growth")
        assert result.status == MetricStatus.MISSING_INPUTS
        assert result.value is None
        assert "at least two consecutive years" in result.notes

    def test_zero_baseline_is_invalid_not_crash(self):
        facts = [
            FactPoint(M.REVENUE, 0.0, "2023", P.YEAR, V.ACTUAL),
            FactPoint(M.REVENUE, 50.0, "2024", P.YEAR, V.ACTUAL),
        ]
        results = calculate_growth_metrics(facts)
        result = _find(results, "revenue_yoy_growth", "2024")
        assert result.status == MetricStatus.INVALID

    def test_non_consecutive_years_flagged_as_period_mismatch(self):
        facts = [
            FactPoint(M.REVENUE, 20.0, "2022", P.YEAR, V.ACTUAL),
            FactPoint(M.REVENUE, 50.0, "2025", P.YEAR, V.ACTUAL),
        ]
        results = calculate_growth_metrics(facts)
        result = _find(results, "revenue_yoy_growth", "2025")
        assert result.status == MetricStatus.PERIOD_MISMATCH

    def test_forecast_values_excluded_from_actual_growth(self):
        """A FORECAST-typed fact must never be silently treated as an actual."""
        facts = [
            FactPoint(M.REVENUE, 96_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
            FactPoint(M.REVENUE, 150_000_000, "2026", P.YEAR, V.FORECAST, "USD"),
        ]
        results = calculate_growth_metrics(facts)
        result = _find(results, "revenue_yoy_growth")
        assert result.status == MetricStatus.MISSING_INPUTS


class TestProfitabilityMetrics:
    def test_ebitda_margin_2025(self):
        results = calculate_profitability_metrics(marketgo_facts())
        result = _find(results, "ebitda_margin", "2025")
        assert result.status == MetricStatus.CALCULATED
        assert result.value == pytest.approx(0.08333, abs=0.001)
        assert result.display_value == "8.3%"

    def test_net_margin_2025(self):
        results = calculate_profitability_metrics(marketgo_facts())
        result = _find(results, "net_margin", "2025")
        assert result.value == pytest.approx(0.036458, abs=0.001)
        assert result.display_value == "3.6%"

    def test_operating_expense_ratio_2025(self):
        results = calculate_profitability_metrics(marketgo_facts())
        result = _find(results, "operating_expense_ratio", "2025")
        assert result.value == pytest.approx(0.91667, abs=0.001)

    def test_gross_profit_estimate_2025(self):
        results = calculate_profitability_metrics(marketgo_facts())
        result = _find(results, "gross_profit_estimate", "2025")
        assert result.status == MetricStatus.CALCULATED
        assert result.value == pytest.approx(27_840_000, abs=1000)
        assert "did not report gross profit directly" in result.notes

    def test_gross_margin_change(self):
        results = calculate_profitability_metrics(marketgo_facts())
        result = _find(results, "gross_margin_change")
        assert result.value == pytest.approx(0.07, abs=0.001)
        assert result.display_value == "+7.0pp"

    def test_ebitda_transition_to_profitability_is_flagged(self):
        results = calculate_profitability_metrics(marketgo_facts())
        result = _find(results, "ebitda_change")
        assert result.value == pytest.approx(14_000_000, abs=1000)
        assert "transitioned from negative to positive EBITDA" in result.notes

    def test_missing_ebitda_returns_missing_inputs(self):
        facts = [FactPoint(M.REVENUE, 100.0, "2025", P.YEAR, V.ACTUAL)]
        results = calculate_profitability_metrics(facts)
        result = _find(results, "ebitda_margin")
        assert result.status == MetricStatus.MISSING_INPUTS


class TestUnitEconomicsMetrics:
    def test_ltv_cac_ratio_2025_matches_reported_figure(self):
        results = calculate_unit_economics_metrics(marketgo_facts())
        result = _find(results, "ltv_cac_ratio", "2025")
        assert result.status == MetricStatus.CALCULATED
        assert result.value == pytest.approx(8.0952, abs=0.01)
        assert result.display_value == "8.1x"

    def test_revenue_per_registered_customer_distinct_from_mau(self):
        results = calculate_unit_economics_metrics(marketgo_facts())
        per_registered = _find(results, "revenue_per_registered_customer", "2025")
        per_mau = _find(results, "revenue_per_mau", "2025")

        assert per_registered.value == pytest.approx(96_000_000 / 2_800_000, abs=0.01)
        assert per_mau.value == pytest.approx(96_000_000 / 620_000, abs=0.01)
        # The two must never collapse to the same figure — this is the
        # explicit "must not display both as a generic customers metric"
        # requirement.
        assert per_registered.value != per_mau.value
        assert per_registered.inputs[1].name == "Registered Customers"
        assert per_mau.inputs[1].name == "Monthly Active Users"

    def test_revenue_per_order_2025(self):
        results = calculate_unit_economics_metrics(marketgo_facts())
        result = _find(results, "revenue_per_order", "2025")
        assert result.value == pytest.approx(96_000_000 / 14_500_000, abs=0.01)

    def test_orders_per_active_user_is_period_mismatch_not_calculated(self):
        """Orders (annual) / MAU (monthly) must never be silently computed."""
        results = calculate_unit_economics_metrics(marketgo_facts())
        result = _find(results, "orders_per_active_user")
        assert result.status == MetricStatus.PERIOD_MISMATCH
        assert result.value is None

    def test_cac_payback_is_missing_inputs_not_fabricated(self):
        results = calculate_unit_economics_metrics(marketgo_facts())
        result = _find(results, "cac_payback_months")
        assert result.status == MetricStatus.MISSING_INPUTS
        assert "monthly revenue per customer" in result.notes


class TestValuationMetrics:
    def test_valuation_to_revenue(self):
        results = calculate_valuation_metrics(marketgo_facts())
        result = _find(results, "valuation_to_revenue", "2025")
        assert result.value == pytest.approx(280_000_000 / 96_000_000, abs=0.001)

    def test_valuation_to_ebitda(self):
        results = calculate_valuation_metrics(marketgo_facts())
        result = _find(results, "valuation_to_ebitda", "2025")
        assert result.value == pytest.approx(280_000_000 / 8_000_000, abs=0.001)

    def test_revenue_per_dollar_raised(self):
        results = calculate_valuation_metrics(marketgo_facts())
        result = _find(results, "revenue_per_dollar_raised", "2025")
        assert result.value == pytest.approx(96_000_000 / 45_000_000, abs=0.001)

    def test_funding_pct_of_post_money(self):
        results = calculate_valuation_metrics(marketgo_facts())
        result = _find(results, "funding_pct_of_post_money", "2025")
        assert result.value == pytest.approx(45_000_000 / 280_000_000, abs=0.001)
        assert result.display_value == "0.2x"

    def test_funding_never_confused_with_revenue(self):
        """Funding and valuation must never appear as a 'revenue' fact."""
        facts = marketgo_facts()
        revenue_facts = [f for f in facts if f.metric == M.REVENUE]
        assert all(f.value != 45_000_000 for f in revenue_facts)
        assert all(f.value != 280_000_000 for f in revenue_facts)


class TestFullEngine:
    def test_calculate_all_derived_metrics_runs_without_error(self):
        results = calculate_all_derived_metrics(marketgo_facts())
        assert len(results) > 0
        # Every result must be a well-formed DerivedMetricResult with a
        # formula present regardless of status.
        assert all(r.formula for r in results)

    def test_team_data_has_no_derived_metrics(self):
        """Team info isn't a FinancialMetricType at all — confirms the
        engine has no way to fabricate team-related figures, matching
        the spec's requirement that missing team data be explicitly
        flagged (by the coverage service, a later step) rather than
        silently scored."""
        results = calculate_all_derived_metrics(marketgo_facts())
        assert not any("team" in r.metric for r in results)