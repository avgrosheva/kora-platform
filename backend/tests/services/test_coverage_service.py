"""Unit tests for the explainable coverage/confidence assessment service."""

from app.models.financial_fact import FinancialMetricType as M
from app.services.coverage_service import (
    REQUIRED_COMPANY_FIELDS,
    REQUIRED_FINANCIAL_METRICS,
    REQUIRED_TEAM_FIELDS,
    compute_coverage,
)


class TestComputeCoverage:
    def test_full_coverage_yields_confidence_near_one(self):
        result = compute_coverage(
            financial_metrics_found=set(REQUIRED_FINANCIAL_METRICS),
            company_fields_found=set(REQUIRED_COMPANY_FIELDS),
            market_fields_found={"market_size", "competitors", "competitive_advantages", "market_risks"},
            team_fields_found=set(REQUIRED_TEAM_FIELDS),
            citations_count=20,
            total_extracted_fields=20,
        )
        assert result.overall_confidence == 1.0
        assert result.coverage["team"].score == 1.0

    def test_missing_team_data_shows_zero_not_error(self):
        """Matches the MarketGo scenario: no team info anywhere in the source."""
        result = compute_coverage(
            financial_metrics_found={M.REVENUE, M.EBITDA},
            company_fields_found={"company_name", "industry"},
            market_fields_found={"competitors"},
            team_fields_found=set(),
            citations_count=5,
            total_extracted_fields=10,
        )
        assert result.coverage["team"].found == 0
        assert result.coverage["team"].score == 0.0
        # Overall confidence should be pulled down but not to zero,
        # since other categories have partial coverage.
        assert 0.0 < result.overall_confidence < 1.0

    def test_critical_missing_fields_flagged(self):
        result = compute_coverage(
            financial_metrics_found={M.REVENUE},
            company_fields_found=set(),
            market_fields_found=set(),
            team_fields_found=set(),
            citations_count=0,
            total_extracted_fields=1,
        )
        assert "cap_table" in result.critical_missing_fields
        assert "debt" in result.critical_missing_fields
        assert "cohort_retention" in result.critical_missing_fields

    def test_source_coverage_computed_correctly(self):
        result = compute_coverage(
            financial_metrics_found={M.REVENUE},
            company_fields_found=set(),
            market_fields_found=set(),
            team_fields_found=set(),
            citations_count=3,
            total_extracted_fields=10,
        )
        assert result.source_coverage == 0.3

    def test_zero_extracted_fields_does_not_divide_by_zero(self):
        result = compute_coverage(
            financial_metrics_found=set(),
            company_fields_found=set(),
            market_fields_found=set(),
            team_fields_found=set(),
            citations_count=0,
            total_extracted_fields=0,
        )
        assert result.source_coverage == 0.0