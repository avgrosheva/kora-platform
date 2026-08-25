"""Unit tests for the unified findings facade.

Mirrors test_evidence_service.py's split: the pure wrapping/inference
functions are tested directly with plain ORM instances (no database);
`FindingsService.get_findings` (the async, DB-facing method) is tested
with a mocked session, proving the wiring without a real database.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.validation_finding import ValidationFinding
from app.models.qualitative_fact import QualitativeFact
from app.services.findings_service import (
    FindingSeverity,
    FindingType,
    FindingsService,
    findings_from_qualitative_risks,
    findings_from_validation,
    run_inference_rules,
)


def _validation_finding(
    severity="warning",
    category="financial_consistency",
    title="EBITDA exceeds revenue",
    description="EBITDA ($5M) exceeds revenue ($4M) for 2025.",
    affected_metrics=None,
    suggested_question="Can you clarify how EBITDA can exceed revenue?",
) -> ValidationFinding:
    return ValidationFinding(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        severity=severity,
        category=category,
        title=title,
        description=description,
        affected_metrics=["ebitda", "revenue"] if affected_metrics is None else affected_metrics,
        sources=[],
        suggested_question=suggested_question,
    )


def _qualitative_fact(
    category: str,
    claim_text: str = "A qualitative claim.",
    severity_hint: str | None = "medium",
    fact_type: str = "document_stated",
) -> QualitativeFact:
    return QualitativeFact(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        category=category,
        claim_text=claim_text,
        fact_type=fact_type,
        severity_hint=severity_hint,
        confidence=0.8,
        source_citation_id=None,
    )


class TestFindingsFromValidation:
    def test_wraps_as_deterministic_type(self):
        findings = findings_from_validation([_validation_finding()])
        assert findings[0].type == FindingType.DETERMINISTIC

    def test_critical_maps_to_critical(self):
        findings = findings_from_validation([_validation_finding(severity="critical")])
        assert findings[0].severity == FindingSeverity.CRITICAL

    def test_info_maps_to_informational(self):
        findings = findings_from_validation([_validation_finding(severity="info")])
        assert findings[0].severity == FindingSeverity.INFORMATIONAL

    def test_warning_maps_to_medium_not_high_or_low(self):
        """The 3-level source scale doesn't distinguish high/low --
        mapping "warning" to the middle of the 5-level scale avoids
        overclaiming a precision the source doesn't have."""
        findings = findings_from_validation([_validation_finding(severity="warning")])
        assert findings[0].severity == FindingSeverity.MEDIUM

    def test_fields_map_through_correctly(self):
        finding = findings_from_validation([_validation_finding()])[0]
        assert finding.title == "EBITDA exceeds revenue"
        assert finding.category == "financial_consistency"
        assert finding.evidence == "ebitda, revenue"
        assert finding.explanation == "EBITDA ($5M) exceeds revenue ($4M) for 2025."
        assert finding.recommended_next_step == "Can you clarify how EBITDA can exceed revenue?"
        assert finding.implication is None

    def test_no_affected_metrics_yields_no_evidence(self):
        finding = findings_from_validation([_validation_finding(affected_metrics=[])])[0]
        assert finding.evidence is None

    def test_empty_list_produces_no_findings(self):
        assert findings_from_validation([]) == []


class TestFindingsFromQualitativeRisks:
    def test_risk_fact_with_severity_hint_becomes_a_finding(self):
        findings = findings_from_qualitative_risks([_qualitative_fact("team_risk", severity_hint="high")])
        assert len(findings) == 1
        assert findings[0].type == FindingType.DOCUMENT_STATED
        assert findings[0].severity == FindingSeverity.HIGH

    def test_opportunity_with_no_severity_hint_is_not_a_finding(self):
        """Matches the plan's "qualitative_facts flagged as risks" scope
        -- an opportunity has no risk dimension and severity_hint=None
        by construction (Step 4's extraction prompt)."""
        findings = findings_from_qualitative_risks([_qualitative_fact("opportunity", severity_hint=None)])
        assert findings == []

    def test_evidence_is_the_claim_text(self):
        finding = findings_from_qualitative_risks(
            [_qualitative_fact("customer_risk", claim_text="Top customer is 60% of revenue.")]
        )[0]
        assert finding.evidence == "Top customer is 60% of revenue."

    def test_no_fabricated_explanation_or_implication(self):
        """A document-stated finding must not carry text beyond what the
        document itself says -- explanation/implication stay None."""
        finding = findings_from_qualitative_risks([_qualitative_fact("legal_regulatory")])[0]
        assert finding.explanation is None
        assert finding.implication is None
        assert finding.recommended_next_step is None

    def test_title_is_a_readable_category_label(self):
        finding = findings_from_qualitative_risks([_qualitative_fact("market_risk")])[0]
        assert finding.title == "Market Risk"


class TestInferenceRules:
    def test_operational_dependency_triggers_concentration_risk_finding(self):
        findings = run_inference_rules([_qualitative_fact("operational_dependency", severity_hint="high")])
        assert len(findings) == 1
        assert findings[0].type == FindingType.AI_INFERRED
        assert "Kora-inferred" in findings[0].title
        assert findings[0].severity == FindingSeverity.HIGH

    def test_ip_ownership_triggers_diligence_risk_finding(self):
        findings = run_inference_rules([_qualitative_fact("ip_ownership")])
        assert len(findings) == 1
        assert findings[0].category == "ip_ownership"
        assert findings[0].type == FindingType.AI_INFERRED

    def test_team_risk_triggers_continuity_risk_finding(self):
        findings = run_inference_rules([_qualitative_fact("team_risk")])
        assert len(findings) == 1
        assert "Continuity" in findings[0].title

    def test_inferred_findings_always_have_an_implication_and_next_step(self):
        """Unlike document-stated findings, AI_INFERRED findings ARE
        allowed to carry implication/recommended_next_step -- that's
        precisely the point of an inference layer, as long as it's
        visibly labeled (type=AI_INFERRED, title says "Kora-inferred")."""
        for category in ("operational_dependency", "ip_ownership", "team_risk"):
            finding = run_inference_rules([_qualitative_fact(category)])[0]
            assert finding.implication is not None
            assert finding.recommended_next_step is not None
            assert finding.type == FindingType.AI_INFERRED

    def test_categories_with_no_rule_produce_no_inference(self):
        findings = run_inference_rules([
            _qualitative_fact("customer_risk"),
            _qualitative_fact("market_risk"),
            _qualitative_fact("other"),
        ])
        assert findings == []

    def test_no_qualitative_facts_produces_no_inference(self):
        assert run_inference_rules([]) == []

    def test_multiple_facts_same_category_each_get_their_own_finding(self):
        findings = run_inference_rules([
            _qualitative_fact("operational_dependency", claim_text="Single payment processor."),
            _qualitative_fact("operational_dependency", claim_text="Single cloud hosting provider."),
        ])
        assert len(findings) == 2


@pytest.fixture
def mock_db():
    """A placeholder session -- both service calls FindingsService
    delegates to are monkeypatched directly in these tests, so `db` is
    never actually used, only passed through."""
    return AsyncMock()


class TestFindingsServiceGetFindings:
    async def test_combines_all_three_sources(self, mock_db, monkeypatch):
        monkeypatch.setattr(
            "app.services.findings_service.ValidationService.list_findings",
            AsyncMock(return_value=[_validation_finding()]),
        )
        monkeypatch.setattr(
            "app.services.findings_service.QualitativeFactsService.list_facts",
            AsyncMock(return_value=[
                _qualitative_fact("customer_risk", severity_hint="low"),
                _qualitative_fact("operational_dependency", severity_hint="high"),
            ]),
        )

        findings = await FindingsService.get_findings(mock_db, uuid.uuid4())

        types = [f.type for f in findings]
        # 1 deterministic + 2 document_stated (both risk facts) + 1
        # ai_inferred (only operational_dependency has a rule).
        assert types.count(FindingType.DETERMINISTIC) == 1
        assert types.count(FindingType.DOCUMENT_STATED) == 2
        assert types.count(FindingType.AI_INFERRED) == 1
        assert len(findings) == 4

    async def test_empty_sources_produce_empty_findings(self, mock_db, monkeypatch):
        monkeypatch.setattr(
            "app.services.findings_service.ValidationService.list_findings",
            AsyncMock(return_value=[]),
        )
        monkeypatch.setattr(
            "app.services.findings_service.QualitativeFactsService.list_facts",
            AsyncMock(return_value=[]),
        )

        findings = await FindingsService.get_findings(mock_db, uuid.uuid4())
        assert findings == []
