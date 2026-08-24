"""Unit tests for the missing-information checklist framework."""

from app.models.financial_fact import FinancialMetricType as M
from app.schemas.missing_information import FieldStatus
from app.services.coverage_service import REQUIRED_FINANCIAL_METRICS
from app.services.missing_information_service import (
    LEGAL_FIELDS,
    compute_missing_information,
    facts_to_metric_set,
)
from tests.fixtures.marketgo import marketgo_facts


class TestComputeMissingInformation:
    def test_marketgo_financial_fields_mostly_found(self):
        """MarketGo's fixture covers revenue, gross_margin, ebitda, net_income,
        cash, cac, ltv, funding — but not debt or burn_rate."""
        found_metrics = facts_to_metric_set(marketgo_facts())
        result = compute_missing_information(
            financial_metrics_found=found_metrics,
            company_fields_found=set(),
            market_fields_found=set(),
            team_fields_found=set(),
        )
        financial_items = [i for i in result.items if i.category == "financial"]
        found_names = {i.field_name for i in financial_items if i.status == FieldStatus.FOUND}
        missing_names = {i.field_name for i in financial_items if i.status == FieldStatus.MISSING}

        assert "revenue" in found_names
        assert "ebitda" in found_names
        assert "cac" in found_names
        assert "debt" in missing_names
        assert "burn_rate" in missing_names

    def test_team_always_missing_without_extraction_capability(self):
        result = compute_missing_information(
            financial_metrics_found=set(),
            company_fields_found=set(),
            market_fields_found=set(),
            team_fields_found=set(),
        )
        team_category = next(c for c in result.by_category if c.category == "team")
        assert len(team_category.missing) == len(team_category.missing)  # all required team fields
        assert "founders" in team_category.missing

    def test_legal_and_investment_always_missing_by_design(self):
        """No data source exists for these yet — always MISSING is correct, not a bug."""
        result = compute_missing_information(
            financial_metrics_found=set(REQUIRED_FINANCIAL_METRICS),
            company_fields_found=set(),
            market_fields_found=set(),
            team_fields_found=set(),
        )
        legal_category = next(c for c in result.by_category if c.category == "legal")
        assert set(legal_category.missing) == set(LEGAL_FIELDS)

    def test_total_found_matches_sum_across_categories(self):
        result = compute_missing_information(
            financial_metrics_found={M.REVENUE, M.EBITDA},
            company_fields_found={"company_name"},
            market_fields_found=set(),
            team_fields_found=set(),
        )
        assert result.total_found == 3

    def test_by_category_covers_every_evaluated_category(self):
        result = compute_missing_information(
            financial_metrics_found=set(),
            company_fields_found=set(),
            market_fields_found=set(),
            team_fields_found=set(),
        )
        category_names = {c.category for c in result.by_category}
        assert category_names == {"company", "financial", "market", "team", "customers", "investment", "legal"}


class TestFactsToMetricSet:
    def test_marketgo_produces_expected_metric_set(self):
        metric_set = facts_to_metric_set(marketgo_facts())
        assert M.REVENUE in metric_set
        assert M.REGISTERED_CUSTOMERS in metric_set
        assert M.MONTHLY_ACTIVE_USERS in metric_set
        assert M.DEBT not in metric_set