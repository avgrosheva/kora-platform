"""Explainable analysis-coverage assessment.

Replaces a single opaque confidence percentage with a per-category
breakdown of what was found versus what a thorough due-diligence
checklist requires. This is deliberately NOT a proxy for investment
quality — a company with excellent fundamentals but a thin source
document will show low coverage, and a company with mediocre
fundamentals but a rich document will show high coverage. The two
should never be conflated; UI copy referencing this data must use
labels like "Analysis coverage" or "Data confidence", never
"investment probability" or similar.
"""

from app.models.financial_fact import FinancialMetricType as M
from app.schemas.coverage import CategoryCoverage, CoverageAssessmentResult

# The Section 10 checklist, expressed as required financial metrics
# (checkable against FinancialFact) and required analysis fields
# (checkable against DocumentAnalysis). Team fields are always
# "required" but the platform has no team-extraction capability yet
# (documented gap from the Investment Scoring milestone) — this
# category will always show 0 found until that capability exists,
# which is itself useful signal, not a bug to hide.
REQUIRED_FINANCIAL_METRICS: list[M] = [
    M.REVENUE, M.GROSS_MARGIN, M.EBITDA, M.NET_INCOME, M.CASH, M.DEBT,
    M.BURN_RATE, M.CAC, M.LTV, M.FUNDING_AMOUNT,
]
REQUIRED_COMPANY_FIELDS = [
    "company_name", "industry", "business_model", "summary",
    "key_products", "revenue_streams", "customers", "competitors",
]
REQUIRED_TEAM_FIELDS = ["founders", "key_executives", "headcount", "hiring_plan", "key_person_dependency"]
REQUIRED_MARKET_FIELDS = ["market_size", "competitors", "competitive_advantages", "market_risks"]

CRITICAL_FIELDS = ["cap_table", "debt", "cohort_retention"]


def compute_coverage(
    financial_metrics_found: set[M],
    company_fields_found: set[str],
    market_fields_found: set[str],
    team_fields_found: set[str],
    citations_count: int,
    total_extracted_fields: int,
    ambiguities_count: int = 0,
) -> CoverageAssessmentResult:
    """Compute a per-category, explainable coverage assessment.

    Args:
        financial_metrics_found: Which of `REQUIRED_FINANCIAL_METRICS`
            were actually found for this document.
        company_fields_found: Which of `REQUIRED_COMPANY_FIELDS` were
            found.
        market_fields_found: Which of `REQUIRED_MARKET_FIELDS` were
            found.
        team_fields_found: Which of `REQUIRED_TEAM_FIELDS` were found
            (expected to be empty given the current lack of team
            extraction).
        citations_count: The number of extracted fields that have at
            least one `SourceCitation`.
        total_extracted_fields: The total number of fields extracted
            (found, regardless of citation), used as the denominator
            for `source_coverage`.
        ambiguities_count: The number of fields with multiple candidate
            values found during extraction.

    Returns:
        The computed `CoverageAssessmentResult`.
    """
    required_financial_found = financial_metrics_found & set(REQUIRED_FINANCIAL_METRICS)
    financial_score = len(required_financial_found) / len(REQUIRED_FINANCIAL_METRICS)
    company_score = len(company_fields_found) / len(REQUIRED_COMPANY_FIELDS)
    market_score = len(market_fields_found) / len(REQUIRED_MARKET_FIELDS)
    team_score = len(team_fields_found) / len(REQUIRED_TEAM_FIELDS)

    coverage = {
        "company": CategoryCoverage(
            found=len(company_fields_found), required=len(REQUIRED_COMPANY_FIELDS), score=company_score
        ),
        "financial": CategoryCoverage(
            found=len(financial_metrics_found), required=len(REQUIRED_FINANCIAL_METRICS), score=financial_score
        ),
        "market": CategoryCoverage(
            found=len(market_fields_found), required=len(REQUIRED_MARKET_FIELDS), score=market_score
        ),
        "team": CategoryCoverage(
            found=len(team_fields_found), required=len(REQUIRED_TEAM_FIELDS), score=team_score
        ),
    }

    overall_confidence = sum(c.score for c in coverage.values()) / len(coverage)
    source_coverage = citations_count / total_extracted_fields if total_extracted_fields else 0.0

    all_found = financial_metrics_found | company_fields_found | market_fields_found | team_fields_found
    critical_missing = [f for f in CRITICAL_FIELDS if f not in {str(x) for x in all_found}]

    return CoverageAssessmentResult(
        overall_confidence=round(overall_confidence, 2),
        coverage=coverage,
        source_coverage=round(source_coverage, 2),
        ambiguities_count=ambiguities_count,
        critical_missing_fields=critical_missing,
    )