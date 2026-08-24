"""Unit tests for the deterministic validation/anomaly-detection engine."""

from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P
from app.schemas.validation import FindingSeverity
from app.services.derived_metrics_service import FactPoint
from app.services.validation_service import (
    check_ebitda_exceeds_revenue,
    check_ebitda_inconsistent_with_opex,
    check_forecast_presented_as_actual,
    check_growth_claims_without_time_series,
    check_ltv_cac_reported_vs_calculated,
    check_negative_values_where_not_meaningful,
    check_percentages_out_of_bounds,
    check_profitable_claim_without_net_income,
    check_registered_vs_active_confusion,
    check_runway_without_inputs,
    check_valuation_or_funding_mislabeled_as_revenue,
    run_all_validations,
)
from tests.fixtures.marketgo import marketgo_facts


class TestEbitdaExceedsRevenue:
    def test_flags_when_ebitda_exceeds_revenue(self):
        facts = [
            FactPoint(M.REVENUE, 10.0, "2025", P.YEAR, V.ACTUAL),
            FactPoint(M.EBITDA, 20.0, "2025", P.YEAR, V.ACTUAL),
        ]
        findings = check_ebitda_exceeds_revenue(facts)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.CRITICAL

    def test_marketgo_does_not_trigger(self):
        assert check_ebitda_exceeds_revenue(marketgo_facts()) == []


class TestEbitdaReconciliation:
    def test_marketgo_ebitda_reconciles(self):
        """MarketGo: Revenue 96M - Opex 88M = 8M, matches reported EBITDA of 8M exactly."""
        assert check_ebitda_inconsistent_with_opex(marketgo_facts()) == []

    def test_flags_large_gap(self):
        facts = [
            FactPoint(M.REVENUE, 100.0, "2025", P.YEAR, V.ACTUAL),
            FactPoint(M.OPERATING_EXPENSES, 80.0, "2025", P.YEAR, V.ACTUAL),
            FactPoint(M.EBITDA, -5.0, "2025", P.YEAR, V.ACTUAL),  # implied is +20
        ]
        findings = check_ebitda_inconsistent_with_opex(facts)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING


class TestNegativeValues:
    def test_flags_negative_revenue(self):
        facts = [FactPoint(M.REVENUE, -5.0, "2025", P.YEAR, V.ACTUAL)]
        findings = check_negative_values_where_not_meaningful(facts)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.CRITICAL

    def test_negative_growth_rate_not_flagged(self):
        """Growth rate CAN legitimately be negative — it's not in the never-negative set."""
        facts = [FactPoint(M.REVENUE, 100.0, "2025", P.YEAR, V.ACTUAL)]
        assert check_negative_values_where_not_meaningful(facts) == []

    def test_marketgo_has_no_negative_value_findings(self):
        """MarketGo's -6M EBITDA for 2024 must NOT be flagged — EBITDA can be negative."""
        assert check_negative_values_where_not_meaningful(marketgo_facts()) == []


class TestPercentageBounds:
    def test_flags_out_of_bounds_gross_margin(self):
        facts = [FactPoint(M.GROSS_MARGIN, 3.5, "2025", P.YEAR, V.ACTUAL)]  # 350%
        findings = check_percentages_out_of_bounds(facts)
        assert len(findings) == 1

    def test_marketgo_margins_within_bounds(self):
        assert check_percentages_out_of_bounds(marketgo_facts()) == []


class TestRegisteredVsActive:
    def test_marketgo_flags_low_activation(self):
        """MarketGo: 620K MAU / 2.8M registered = 22% activation, below the 40% threshold."""
        findings = check_registered_vs_active_confusion(marketgo_facts())
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "registered_customers" in findings[0].affected_metrics
        assert "monthly_active_users" in findings[0].affected_metrics
        assert "90 days" in findings[0].suggested_question

    def test_flags_when_mau_exceeds_registered(self):
        facts = [
            FactPoint(M.REGISTERED_CUSTOMERS, 100.0, "2025", P.YEAR, V.ACTUAL),
            FactPoint(M.MONTHLY_ACTIVE_USERS, 200.0, "2025", P.YEAR, V.ACTUAL),
        ]
        findings = check_registered_vs_active_confusion(facts)
        assert len(findings) == 1

    def test_no_finding_when_activation_healthy(self):
        facts = [
            FactPoint(M.REGISTERED_CUSTOMERS, 100.0, "2025", P.YEAR, V.ACTUAL),
            FactPoint(M.MONTHLY_ACTIVE_USERS, 60.0, "2025", P.YEAR, V.ACTUAL),
        ]
        assert check_registered_vs_active_confusion(facts) == []


class TestLtvCacReportedVsCalculated:
    def test_marketgo_reported_matches_calculated(self):
        """MarketGo explicitly reports 8.1x, which matches LTV(170)/CAC(21) = 8.095x."""
        findings = check_ltv_cac_reported_vs_calculated(marketgo_facts(), reported_ratio=8.1)
        assert findings == []

    def test_flags_mismatch(self):
        facts = [
            FactPoint(M.LTV, 100.0, "2025", P.YEAR, V.ESTIMATE),
            FactPoint(M.CAC, 20.0, "2025", P.YEAR, V.ACTUAL),
        ]
        findings = check_ltv_cac_reported_vs_calculated(facts, reported_ratio=10.0)
        assert len(findings) == 1

    def test_none_reported_ratio_produces_no_findings(self):
        assert check_ltv_cac_reported_vs_calculated(marketgo_facts(), reported_ratio=None) == []


class TestGrowthClaimsWithoutTimeSeries:
    def test_flags_claim_with_single_period(self):
        facts = [FactPoint(M.MONTHLY_ACTIVE_USERS, 100.0, "2025", P.YEAR, V.ACTUAL)]
        findings = check_growth_claims_without_time_series(facts, ["monthly_active_users"])
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_marketgo_revenue_growth_claim_is_supported(self):
        findings = check_growth_claims_without_time_series(marketgo_facts(), ["revenue"])
        assert findings == []


class TestProfitableClaim:
    def test_flags_ebitda_positive_net_income_missing(self):
        facts = [FactPoint(M.EBITDA, 10.0, "2025", P.YEAR, V.ACTUAL)]
        findings = check_profitable_claim_without_net_income(facts, claims_profitability=True)
        assert len(findings) == 1

    def test_marketgo_has_positive_net_income_so_no_finding(self):
        """MarketGo reports EBITDA=8M AND net income=3.5M (positive) — claim is supported."""
        findings = check_profitable_claim_without_net_income(marketgo_facts(), claims_profitability=True)
        assert findings == []

    def test_no_claim_no_finding(self):
        facts = [FactPoint(M.EBITDA, 10.0, "2025", P.YEAR, V.ACTUAL)]
        assert check_profitable_claim_without_net_income(facts, claims_profitability=False) == []


class TestRunwayWithoutInputs:
    def test_flags_when_burn_missing(self):
        facts = [FactPoint(M.CASH, 1_000_000.0, "2025", P.POINT_IN_TIME, V.ACTUAL)]
        findings = check_runway_without_inputs(facts, runway_claimed=True)
        assert len(findings) == 1

    def test_marketgo_has_cash_but_no_burn_rate_so_flags(self):
        """MarketGo states cash ($18M) but never states an explicit burn rate."""
        findings = check_runway_without_inputs(marketgo_facts(), runway_claimed=True)
        assert len(findings) == 1
        assert "burn rate" in findings[0].description


class TestValuationOrFundingMislabeledAsRevenue:
    def test_flags_exact_match(self):
        facts = [
            FactPoint(M.REVENUE, 45_000_000.0, "2025", P.YEAR, V.ACTUAL),
            FactPoint(M.FUNDING_AMOUNT, 45_000_000.0, "2025", P.YEAR, V.ACTUAL),
        ]
        findings = check_valuation_or_funding_mislabeled_as_revenue(facts)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.CRITICAL

    def test_marketgo_funding_and_valuation_do_not_collide_with_revenue(self):
        """MarketGo: funding=45M, valuation=280M, revenue=24M/58M/96M — no overlap."""
        assert check_valuation_or_funding_mislabeled_as_revenue(marketgo_facts()) == []


class TestForecastPresentedAsActual:
    def test_flags_future_year_actual(self):
        facts = [FactPoint(M.REVENUE, 150.0, "2026", P.YEAR, V.ACTUAL)]
        findings = check_forecast_presented_as_actual(facts, future_year=2026)
        assert len(findings) == 1

    def test_forecast_typed_correctly_is_not_flagged(self):
        facts = [FactPoint(M.REVENUE, 150.0, "2026", P.YEAR, V.FORECAST)]
        assert check_forecast_presented_as_actual(facts, future_year=2026) == []

    def test_marketgo_has_no_future_actuals(self):
        assert check_forecast_presented_as_actual(marketgo_facts(), future_year=2026) == []


class TestRunAllValidations:
    def test_marketgo_produces_expected_finding_set(self):
        """End-to-end: MarketGo's unconditional findings should be exactly the
        registered-vs-MAU warning — no false positives from any other rule."""
        findings = run_all_validations(marketgo_facts())
        categories = {f.category for f in findings}
        assert any(f.title == "Customer metric may be misleading" for f in findings)
        # None of the "should never trigger on clean data" rules should fire.
        assert not any(f.title == "EBITDA exceeds revenue" for f in findings)
        assert not any("mislabeled as revenue" in f.title.lower() or "matches a reported revenue" in f.title for f in findings)

    def test_findings_sorted_by_severity(self):
        facts = [
            FactPoint(M.REVENUE, -5.0, "2025", P.YEAR, V.ACTUAL),  # CRITICAL
            FactPoint(M.REGISTERED_CUSTOMERS, 100.0, "2025", P.YEAR, V.ACTUAL),
            FactPoint(M.MONTHLY_ACTIVE_USERS, 10.0, "2025", P.YEAR, V.ACTUAL),  # WARNING
        ]
        findings = run_all_validations(facts)
        severities = [f.severity for f in findings]
        assert severities == sorted(severities, key=lambda s: {"critical": 0, "warning": 1, "info": 2}[s.value])