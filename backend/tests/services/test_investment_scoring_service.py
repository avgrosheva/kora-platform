"""Unit tests for the scoring redesign (Evidence Layer plan, Step 8).

Pure-function/strategy tests: no database, no AI call.
`DeterministicScoringStrategy.compute()` is exercised directly against
plain (unpersisted) ORM instances, matching this project's established
pattern for testing scoring/coverage logic without a session.
"""

import uuid

from app.models.document_analysis import DocumentAnalysis
from app.models.financial_metrics import FinancialMetrics
from app.models.investment_score import AssessmentStatus
from app.services.investment_scoring_service import (
    DeterministicScoringStrategy,
    _compute_assessment_status,
)

strategy = DeterministicScoringStrategy()


def _financial_metrics(**overrides) -> FinancialMetrics:
    defaults = dict(
        document_id=uuid.uuid4(), currency="USD", revenue=None, arr=None, mrr=None,
        gross_margin=None, ebitda=None, burn_rate=None, runway_months=None, cash=None,
        customers=None, growth_rate=None, cac=None, ltv=None, valuation=None, confidence_score=None,
    )
    defaults.update(overrides)
    return FinancialMetrics(**defaults)


def _analysis(**overrides) -> DocumentAnalysis:
    defaults = dict(
        document_id=uuid.uuid4(), company_name=None, industry=None, business_model=None,
        summary=None, key_products=None, risks=None, opportunities=None,
        revenue_streams=None, customers=None, competitors=None, raw_json={},
    )
    defaults.update(overrides)
    return DocumentAnalysis(**defaults)


class TestComputeAssessmentStatus:
    def test_all_thresholds_met_is_sufficient(self):
        assert _compute_assessment_status(confidence_score=0.8, coverage_confidence=0.8, assessed_dimensions=4) \
            == AssessmentStatus.SUFFICIENT_EVIDENCE

    def test_low_coverage_alone_is_insufficient(self):
        assert _compute_assessment_status(confidence_score=0.8, coverage_confidence=0.3, assessed_dimensions=4) \
            == AssessmentStatus.INSUFFICIENT_EVIDENCE

    def test_low_confidence_alone_is_insufficient(self):
        assert _compute_assessment_status(confidence_score=0.4, coverage_confidence=0.8, assessed_dimensions=4) \
            == AssessmentStatus.INSUFFICIENT_EVIDENCE

    def test_too_few_assessed_dimensions_is_insufficient(self):
        """The exact bug this step fixes: one dimension alone (e.g. just
        financial_score) is not enough evidence for a composite number,
        even if coverage/confidence both look fine in isolation."""
        assert _compute_assessment_status(confidence_score=0.6, coverage_confidence=0.6, assessed_dimensions=1) \
            == AssessmentStatus.INSUFFICIENT_EVIDENCE

    def test_exactly_at_thresholds_is_sufficient(self):
        """Boundary check: >= , not >."""
        assert _compute_assessment_status(confidence_score=0.5, coverage_confidence=0.5, assessed_dimensions=3) \
            == AssessmentStatus.SUFFICIENT_EVIDENCE


class TestDeterministicScoringStrategyAssessmentStatus:
    def test_single_dimension_with_high_coverage_still_withholds_overall_score(self):
        """Reproduces the exact bug report scenario: only ONE of four
        dimensions has data (here, just financial via ARR), but
        coverage happens to be high. overall_score must still be None,
        not a confident-looking number computed from one dimension."""
        fm = _financial_metrics(arr=12_000_000)  # financial_score computable; growth/risk have nothing
        result = strategy.compute(fm, None, coverage_confidence=0.9)

        assert result.financial_score is not None  # the one dimension IS scored...
        assert result.assessment_status == AssessmentStatus.INSUFFICIENT_EVIDENCE
        assert result.overall_score is None  # ...but no composite is asserted

    def test_full_data_and_high_coverage_yields_sufficient_evidence_and_a_real_score(self):
        fm = _financial_metrics(
            arr=12_000_000, gross_margin=65, ebitda=500_000,
            growth_rate=40, runway_months=24, burn_rate=100_000, revenue=1_000_000,
        )
        analysis = _analysis(
            industry="SaaS", customers=["SMBs"], competitors=["Acme"], revenue_streams=["Subscriptions"],
        )
        result = strategy.compute(fm, analysis, coverage_confidence=0.9)

        assert result.assessment_status == AssessmentStatus.SUFFICIENT_EVIDENCE
        assert result.overall_score is not None
        assert 0 <= result.overall_score <= 100

    def test_no_data_at_all_is_insufficient_and_overall_score_is_none(self):
        result = strategy.compute(None, None, coverage_confidence=0.0)
        assert result.assessment_status == AssessmentStatus.INSUFFICIENT_EVIDENCE
        assert result.overall_score is None

    def test_sub_scores_are_still_populated_even_when_insufficient(self):
        """"Keep per-category scores as observed-performance signals" --
        withholding overall_score must not blank out the sub-scores that
        DO have data."""
        fm = _financial_metrics(arr=12_000_000, growth_rate=40)
        result = strategy.compute(fm, None, coverage_confidence=0.1)  # low coverage forces insufficient

        assert result.assessment_status == AssessmentStatus.INSUFFICIENT_EVIDENCE
        assert result.overall_score is None
        assert result.financial_score is not None
        assert result.growth_score is not None

    def test_reasoning_explains_the_withheld_score_when_insufficient(self):
        fm = _financial_metrics(arr=12_000_000)
        result = strategy.compute(fm, None, coverage_confidence=0.1)
        assert "not yet enough evidence" in result.reasoning

    def test_reasoning_does_not_mention_withholding_when_sufficient(self):
        fm = _financial_metrics(
            arr=12_000_000, gross_margin=65, ebitda=500_000,
            growth_rate=40, runway_months=24, burn_rate=100_000, revenue=1_000_000,
        )
        analysis = _analysis(industry="SaaS", customers=["SMBs"], competitors=["Acme"], revenue_streams=["Subs"])
        result = strategy.compute(fm, analysis, coverage_confidence=0.9)
        assert "not yet enough evidence" not in result.reasoning

    def test_category_breakdown_is_still_produced_when_insufficient(self):
        fm = _financial_metrics(arr=12_000_000)
        result = strategy.compute(fm, None, coverage_confidence=0.1)
        assert result.category_breakdown is not None
        assert result.category_breakdown["financial_score"]["status"] == "assessed"
        assert result.category_breakdown["growth_score"]["status"] == "not_assessable"

    def test_contribution_is_none_when_overall_score_is_withheld(self):
        """"Contributes N pts to the overall score" would be a false
        statement when there is no overall score -- contribution must
        be None even for an assessed dimension in that case."""
        fm = _financial_metrics(arr=12_000_000)
        result = strategy.compute(fm, None, coverage_confidence=0.1)
        assert result.assessment_status == AssessmentStatus.INSUFFICIENT_EVIDENCE
        assert result.category_breakdown["financial_score"]["score"] is not None
        assert result.category_breakdown["financial_score"]["contribution"] is None

    def test_contribution_is_populated_when_overall_score_is_present(self):
        fm = _financial_metrics(
            arr=12_000_000, gross_margin=65, ebitda=500_000,
            growth_rate=40, runway_months=24, burn_rate=100_000, revenue=1_000_000,
        )
        analysis = _analysis(industry="SaaS", customers=["SMBs"], competitors=["Acme"], revenue_streams=["Subs"])
        result = strategy.compute(fm, analysis, coverage_confidence=0.9)
        assert result.assessment_status == AssessmentStatus.SUFFICIENT_EVIDENCE
        assert result.category_breakdown["financial_score"]["contribution"] is not None
