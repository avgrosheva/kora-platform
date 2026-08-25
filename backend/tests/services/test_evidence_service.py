"""Unit tests for the canonical evidence-read facade.

Two layers are tested separately, matching how the module is split:

- The pure normalization functions (`evidence_facts_from_financial_facts`,
  `evidence_facts_from_analysis`, `evidence_contains`) are tested with
  plain Python objects, no database involved — this is where the actual
  business logic (category assignment, fact_type mapping, "found" means
  non-empty) lives, and where a bug would actually hide.
- `EvidenceService.get_evidence`/`has_fact` (the async, DB-facing
  methods) are tested with a mocked `AsyncSession` and a monkeypatched
  `FinancialFactsService.get_fact_points`, so these are still fast,
  hermetic unit tests — no real database — while still exercising the
  actual public methods other services will call in Step 2 onward.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.document_analysis import DocumentAnalysis
from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType, PeriodType
from app.models.qualitative_fact import (
    QualitativeFact,
    QualitativeFactCategory,
    QualitativeFactSeverityHint,
    QualitativeFactType,
)
from app.services.derived_metrics_service import FactPoint
from app.services.evidence_service import (
    EvidenceFactType,
    EvidenceService,
    evidence_contains,
    evidence_facts_from_analysis,
    evidence_facts_from_financial_facts,
    evidence_facts_from_qualitative_facts,
)


def _fact(
    metric: M,
    value: float,
    value_type: FinancialValueType = FinancialValueType.ACTUAL,
    period: str | None = "2025",
) -> FactPoint:
    return FactPoint(metric=metric, value=value, period=period, period_type=PeriodType.YEAR, value_type=value_type)


def _analysis(**overrides) -> DocumentAnalysis:
    defaults = dict(
        document_id=uuid.uuid4(),
        company_name=None,
        industry=None,
        business_model=None,
        summary=None,
        key_products=None,
        risks=None,
        opportunities=None,
        revenue_streams=None,
        customers=None,
        competitors=None,
        raw_json={},
    )
    defaults.update(overrides)
    return DocumentAnalysis(**defaults)


class TestEvidenceFactsFromFinancialFacts:
    def test_actual_fact_is_financial_and_document_stated(self):
        evidence = evidence_facts_from_financial_facts([_fact(M.REVENUE, 96_000_000)])

        assert len(evidence) == 1
        assert evidence[0].category == "financial"
        assert evidence[0].field_name == "revenue"
        assert evidence[0].fact_type == EvidenceFactType.DOCUMENT_STATED
        assert evidence[0].period == "2025"

    def test_forecast_and_estimate_are_also_document_stated(self):
        evidence = evidence_facts_from_financial_facts(
            [
                _fact(M.REVENUE, 120_000_000, value_type=FinancialValueType.FORECAST),
                _fact(M.LTV, 170, value_type=FinancialValueType.ESTIMATE),
            ]
        )
        assert all(fact.fact_type == EvidenceFactType.DOCUMENT_STATED for fact in evidence)

    def test_derived_value_type_is_marked_derived_not_document_stated(self):
        evidence = evidence_facts_from_financial_facts(
            [_fact(M.GROSS_PROFIT, 20_000_000, value_type=FinancialValueType.DERIVED)]
        )
        assert evidence[0].fact_type == EvidenceFactType.DERIVED

    def test_empty_fact_list_produces_no_evidence(self):
        assert evidence_facts_from_financial_facts([]) == []

    def test_distinct_periods_are_preserved_not_collapsed(self):
        evidence = evidence_facts_from_financial_facts(
            [_fact(M.REVENUE, 24_000_000, period="2023"), _fact(M.REVENUE, 96_000_000, period="2025")]
        )
        periods = {fact.period for fact in evidence}
        assert periods == {"2023", "2025"}


class TestEvidenceFactsFromAnalysis:
    def test_populated_scalar_field_is_categorized_company(self):
        evidence = evidence_facts_from_analysis(_analysis(company_name="MarketGo", industry="E-commerce"))

        assert evidence_contains(evidence, "company_name", category="company")
        assert evidence_contains(evidence, "industry", category="company")

    def test_null_scalar_field_produces_no_evidence_fact(self):
        evidence = evidence_facts_from_analysis(_analysis(company_name=None))
        assert not evidence_contains(evidence, "company_name")

    def test_blank_string_field_is_treated_as_missing(self):
        evidence = evidence_facts_from_analysis(_analysis(summary="   "))
        assert not evidence_contains(evidence, "summary")

    def test_empty_array_field_is_treated_as_missing(self):
        evidence = evidence_facts_from_analysis(_analysis(key_products=[]))
        assert not evidence_contains(evidence, "key_products")

    def test_populated_array_field_is_document_stated(self):
        evidence = evidence_facts_from_analysis(_analysis(competitors=["Shopify", "BigCommerce"]))
        match = next(fact for fact in evidence if fact.field_name == "competitors")
        assert match.fact_type == EvidenceFactType.DOCUMENT_STATED
        assert match.value == ["Shopify", "BigCommerce"]

    def test_competitors_is_categorized_company(self):
        """coverage_service.py lists "competitors" in both
        REQUIRED_COMPANY_FIELDS and REQUIRED_MARKET_FIELDS; EvidenceService
        breaks the tie in favor of "company" since that's the field's real
        home on the DocumentAnalysis model. See _ANALYSIS_FIELD_CATEGORY.
        """
        evidence = evidence_facts_from_analysis(_analysis(competitors=["Shopify"]))
        assert evidence_contains(evidence, "competitors", category="company")
        assert not evidence_contains(evidence, "competitors", category="market")

    def test_risks_and_opportunities_are_visible_as_evidence(self):
        evidence = evidence_facts_from_analysis(
            _analysis(risks=["customer concentration"], opportunities=["international expansion"])
        )
        assert evidence_contains(evidence, "risks", category="company")
        assert evidence_contains(evidence, "opportunities", category="company")

    def test_fully_empty_analysis_produces_no_evidence(self):
        assert evidence_facts_from_analysis(_analysis()) == []


def _qualitative_fact(
    category: QualitativeFactCategory,
    claim_text: str = "A qualitative claim.",
    severity_hint: QualitativeFactSeverityHint | None = None,
    fact_type: QualitativeFactType = QualitativeFactType.DOCUMENT_STATED,
    confidence: float | None = 0.8,
    source_citation_id=None,
) -> QualitativeFact:
    return QualitativeFact(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        category=category.value,
        claim_text=claim_text,
        fact_type=fact_type.value,
        severity_hint=severity_hint.value if severity_hint else None,
        confidence=confidence,
        source_citation_id=source_citation_id,
    )


class TestEvidenceFactsFromQualitativeFacts:
    def test_team_risk_is_categorized_team(self):
        evidence = evidence_facts_from_qualitative_facts(
            [_qualitative_fact(QualitativeFactCategory.TEAM_RISK, severity_hint=QualitativeFactSeverityHint.MEDIUM)]
        )
        assert evidence[0].category == "team"

    def test_market_risk_is_categorized_market_and_matches_the_checklist_field(self):
        """market_risk is the one category with an unambiguous 1:1 match
        to coverage_service.REQUIRED_MARKET_FIELDS' "market_risks" item —
        see _field_name_for_qualitative_fact."""
        evidence = evidence_facts_from_qualitative_facts(
            [_qualitative_fact(QualitativeFactCategory.MARKET_RISK, severity_hint=QualitativeFactSeverityHint.HIGH)]
        )
        assert evidence[0].category == "market"
        assert evidence[0].field_name == "market_risks"

    def test_two_market_risk_facts_collapse_to_the_same_field_name(self):
        """Multiple distinct market-risk claims are still one checklist
        item ("was market_risks ever found"), not N separate ones."""
        evidence = evidence_facts_from_qualitative_facts([
            _qualitative_fact(QualitativeFactCategory.MARKET_RISK, claim_text="Claim A"),
            _qualitative_fact(QualitativeFactCategory.MARKET_RISK, claim_text="Claim B"),
        ])
        assert {e.field_name for e in evidence} == {"market_risks"}

    def test_other_risk_categories_fall_back_to_company_with_unique_field_names(self):
        facts = [
            _qualitative_fact(QualitativeFactCategory.CUSTOMER_RISK),
            _qualitative_fact(QualitativeFactCategory.LEGAL_REGULATORY),
            _qualitative_fact(QualitativeFactCategory.OPERATIONAL_DEPENDENCY),
            _qualitative_fact(QualitativeFactCategory.IP_OWNERSHIP),
            _qualitative_fact(QualitativeFactCategory.OPPORTUNITY),
            _qualitative_fact(QualitativeFactCategory.OTHER),
        ]
        evidence = evidence_facts_from_qualitative_facts(facts)
        assert all(e.category == "company" for e in evidence)
        # Every fact gets its own field name -- none collide, unlike
        # market_risks above.
        assert len({e.field_name for e in evidence}) == len(facts)

    def test_opportunity_has_no_severity_hint(self):
        evidence = evidence_facts_from_qualitative_facts(
            [_qualitative_fact(QualitativeFactCategory.OPPORTUNITY, severity_hint=None)]
        )
        # severity_hint isn't part of EvidenceFact's shape (it's a
        # QualitativeFact-specific field, consumed directly by Step 5's
        # FindingsService) -- this just confirms normalization doesn't
        # choke on a None severity_hint.
        assert evidence[0].value == "A qualitative claim."

    def test_confidence_and_citation_are_carried_through(self):
        citation_id = uuid.uuid4()
        evidence = evidence_facts_from_qualitative_facts(
            [_qualitative_fact(QualitativeFactCategory.TEAM_RISK, confidence=0.65, source_citation_id=citation_id)]
        )
        assert evidence[0].confidence == 0.65
        assert evidence[0].source_citation_id == str(citation_id)

    def test_document_stated_and_ai_inferred_fact_types_map_through(self):
        stated = evidence_facts_from_qualitative_facts(
            [_qualitative_fact(QualitativeFactCategory.OTHER, fact_type=QualitativeFactType.DOCUMENT_STATED)]
        )
        inferred = evidence_facts_from_qualitative_facts(
            [_qualitative_fact(QualitativeFactCategory.OTHER, fact_type=QualitativeFactType.AI_INFERRED)]
        )
        assert stated[0].fact_type == EvidenceFactType.DOCUMENT_STATED
        assert inferred[0].fact_type == EvidenceFactType.AI_INFERRED


class TestEvidenceContains:
    def test_category_filter_separates_financial_from_company(self):
        financial = evidence_facts_from_financial_facts([_fact(M.REVENUE, 1)])
        company = evidence_facts_from_analysis(_analysis(company_name="Acme"))
        combined = financial + company

        assert evidence_contains(combined, "revenue", category="financial")
        assert not evidence_contains(combined, "revenue", category="company")
        assert evidence_contains(combined, "company_name", category="company")
        assert not evidence_contains(combined, "company_name", category="financial")

    def test_no_category_filter_matches_regardless_of_category(self):
        evidence = evidence_facts_from_financial_facts([_fact(M.REVENUE, 1)])
        assert evidence_contains(evidence, "revenue")


class _FakeScalarResult:
    """Stand-in for the SQLAlchemy Result object `db.execute` returns.

    `EvidenceService.get_evidence` now issues two `db.execute` calls
    (the `DocumentAnalysis` lookup and, via `QualitativeFactsService`,
    the `QualitativeFact` lookup), and `mock_db.execute` returns the
    same configured value for both — so this stub supports both call
    shapes: `.scalar_one_or_none()` for the former, `.scalars().all()`
    for the latter (always empty here; no test in this class exercises
    qualitative facts — see test_qualitative_facts.py for that).
    """

    def __init__(self, scalar):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return []


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestEvidenceServiceHasFact:
    """Exercises the real async facade methods with a mocked session —
    no real database — proving the DB-facing wiring, not just the pure
    normalization functions above, works end to end.
    """

    async def test_fact_present_in_financial_facts_is_visible_via_has_fact(self, mock_db, monkeypatch):
        mock_db.execute.return_value = _FakeScalarResult(None)  # no DocumentAnalysis row
        monkeypatch.setattr(
            "app.services.evidence_service.FinancialFactsService.get_fact_points",
            AsyncMock(return_value=[_fact(M.REVENUE, 96_000_000)]),
        )

        assert await EvidenceService.has_fact(mock_db, uuid.uuid4(), "revenue", category="financial") is True
        assert await EvidenceService.has_fact(mock_db, uuid.uuid4(), "ebitda") is False

    async def test_fact_present_in_document_analysis_is_visible_via_has_fact(self, mock_db, monkeypatch):
        mock_db.execute.return_value = _FakeScalarResult(_analysis(company_name="Acme"))
        monkeypatch.setattr(
            "app.services.evidence_service.FinancialFactsService.get_fact_points",
            AsyncMock(return_value=[]),
        )

        assert await EvidenceService.has_fact(mock_db, uuid.uuid4(), "company_name", category="company") is True
        # Present, but under the wrong category filter -> not visible.
        assert await EvidenceService.has_fact(mock_db, uuid.uuid4(), "company_name", category="financial") is False

    async def test_no_analysis_row_and_no_financial_facts_is_not_an_error(self, mock_db, monkeypatch):
        mock_db.execute.return_value = _FakeScalarResult(None)
        monkeypatch.setattr(
            "app.services.evidence_service.FinancialFactsService.get_fact_points",
            AsyncMock(return_value=[]),
        )

        evidence = await EvidenceService.get_evidence(mock_db, uuid.uuid4())
        assert evidence == []

    async def test_category_filter_on_get_evidence_spans_both_sources(self, mock_db, monkeypatch):
        mock_db.execute.return_value = _FakeScalarResult(_analysis(company_name="Acme", industry="SaaS"))
        monkeypatch.setattr(
            "app.services.evidence_service.FinancialFactsService.get_fact_points",
            AsyncMock(return_value=[_fact(M.REVENUE, 1), _fact(M.EBITDA, 2)]),
        )

        financial_only = await EvidenceService.get_evidence(mock_db, uuid.uuid4(), category="financial")
        company_only = await EvidenceService.get_evidence(mock_db, uuid.uuid4(), category="company")

        assert {fact.field_name for fact in financial_only} == {"revenue", "ebitda"}
        assert {fact.field_name for fact in company_only} == {"company_name", "industry"}

    async def test_fields_found_returns_flat_set_for_category(self, mock_db, monkeypatch):
        mock_db.execute.return_value = _FakeScalarResult(_analysis(company_name="Acme", industry="SaaS"))
        monkeypatch.setattr(
            "app.services.evidence_service.FinancialFactsService.get_fact_points",
            AsyncMock(return_value=[]),
        )

        found = await EvidenceService.fields_found(mock_db, uuid.uuid4(), category="company")
        assert found == {"company_name", "industry"}
