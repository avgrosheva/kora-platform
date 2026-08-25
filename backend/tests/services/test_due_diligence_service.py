"""Unit tests for due diligence prompt construction and the post-
generation critical-findings check (Evidence Layer plan, Step 6 — Bug C
fix).

These are pure-function tests: no database, no AI call. The full,
database-backed reproduction of Bug C itself (an LLM narrative saying
"no red flags" while findings are non-empty) lives in
tests/integration/test_due_diligence_bug_c.py, since it needs a real
document with persisted findings to be a faithful reproduction.
"""

from app.schemas.due_diligence import DueDiligenceSection
from app.services.evidence_service import EvidenceFact, EvidenceFactType
from app.services.due_diligence_service import (
    _format_evidence,
    _format_findings,
    ensure_critical_findings_are_surfaced,
)
from app.services.findings_service import Finding, FindingSeverity, FindingType


def _evidence(category="financial", field_name="revenue", display_value="$1,000,000", period=None) -> EvidenceFact:
    return EvidenceFact(
        category=category,
        field_name=field_name,
        value=1_000_000,
        display_value=display_value,
        fact_type=EvidenceFactType.DOCUMENT_STATED,
        source_citation_id=None,
        confidence=None,
        period=period,
    )


def _finding(
    title="Some Finding",
    severity=FindingSeverity.MEDIUM,
    type=FindingType.DETERMINISTIC,
    explanation="An explanation.",
    evidence=None,
) -> Finding:
    return Finding(
        title=title, category="financial_consistency", severity=severity, type=type,
        evidence=evidence, explanation=explanation, implication=None, recommended_next_step=None,
    )


class TestFormatEvidence:
    def test_none_returns_not_available_marker(self):
        assert _format_evidence(None) == "Not available."

    def test_empty_list_returns_not_available_marker(self):
        assert _format_evidence([]) == "Not available."

    def test_groups_by_category(self):
        text = _format_evidence([
            _evidence(category="financial", field_name="revenue"),
            _evidence(category="company", field_name="company_name", display_value="Acme"),
        ])
        assert "Financial:" in text
        assert "Company:" in text
        assert "revenue" in text
        assert "company_name" in text

    def test_period_is_included_when_present(self):
        text = _format_evidence([_evidence(field_name="revenue", period="2025")])
        assert "revenue (2025)" in text


class TestFormatFindings:
    def test_none_returns_not_available_marker(self):
        assert _format_findings(None) == "Not available."

    def test_groups_by_severity_in_fixed_order(self):
        text = _format_findings([
            _finding(title="Low Finding", severity=FindingSeverity.LOW),
            _finding(title="Critical Finding", severity=FindingSeverity.CRITICAL),
        ])
        critical_index = text.index("CRITICAL")
        low_index = text.index("LOW")
        assert critical_index < low_index

    def test_type_label_is_included(self):
        text = _format_findings([_finding(type=FindingType.AI_INFERRED)])
        assert "[Kora-inferred]" in text

    def test_document_stated_label_is_distinct_from_deterministic(self):
        text = _format_findings([
            _finding(title="A", type=FindingType.DOCUMENT_STATED),
            _finding(title="B", type=FindingType.DETERMINISTIC),
        ])
        assert "[Document-stated] A" in text
        assert "[Deterministic check] B" in text


class TestEnsureCriticalFindingsAreSurfaced:
    def _sections(self, red_flags_content="No red flags were identified.") -> list[DueDiligenceSection]:
        return [
            DueDiligenceSection(title="Executive Summary", content="A summary."),
            DueDiligenceSection(title="Risks", content="Some general risks."),
            DueDiligenceSection(title="Red Flags", content=red_flags_content),
        ]

    def test_no_critical_or_high_findings_leaves_sections_unchanged(self):
        sections = self._sections()
        result = ensure_critical_findings_are_surfaced(sections, [_finding(severity=FindingSeverity.MEDIUM)])
        assert result == sections

    def test_already_mentioned_finding_is_not_duplicated(self):
        finding = _finding(title="Customer Concentration Risk", severity=FindingSeverity.CRITICAL)
        sections = self._sections(red_flags_content="Customer Concentration Risk is a concern here.")
        result = ensure_critical_findings_are_surfaced(sections, [finding])
        assert result == sections  # untouched -- already mentioned

    def test_this_is_the_exact_bug_c_reproduction(self):
        """The exact contradiction from the bug report: the narrative
        says "no red flags" while a critical finding exists."""
        finding = _finding(
            title="Customer Concentration Risk", severity=FindingSeverity.CRITICAL,
            explanation="One customer represents 85% of revenue.",
        )
        sections = self._sections(red_flags_content="No red flags were identified.")

        result = ensure_critical_findings_are_surfaced(sections, [finding])

        red_flags = next(s for s in result if s.title == "Red Flags")
        assert "No red flags were identified." in red_flags.content  # original text preserved
        assert "Customer Concentration Risk" in red_flags.content  # but now also injected
        assert "85% of revenue" in red_flags.content

    def test_only_red_flags_section_is_modified(self):
        finding = _finding(title="Omitted Critical Thing", severity=FindingSeverity.CRITICAL)
        sections = self._sections()
        result = ensure_critical_findings_are_surfaced(sections, [finding])

        exec_summary = next(s for s in result if s.title == "Executive Summary")
        risks = next(s for s in result if s.title == "Risks")
        assert exec_summary.content == "A summary."
        assert risks.content == "Some general risks."

    def test_high_severity_also_triggers_injection_not_only_critical(self):
        finding = _finding(title="Omitted High Thing", severity=FindingSeverity.HIGH)
        sections = self._sections()
        result = ensure_critical_findings_are_surfaced(sections, [finding])
        red_flags = next(s for s in result if s.title == "Red Flags")
        assert "Omitted High Thing" in red_flags.content

    def test_medium_and_low_severity_do_not_trigger_injection(self):
        findings = [
            _finding(title="Medium Thing", severity=FindingSeverity.MEDIUM),
            _finding(title="Low Thing", severity=FindingSeverity.LOW),
        ]
        sections = self._sections()
        result = ensure_critical_findings_are_surfaced(sections, findings)
        assert result == sections

    def test_multiple_omitted_findings_are_all_injected(self):
        findings = [
            _finding(title="First Critical", severity=FindingSeverity.CRITICAL),
            _finding(title="Second Critical", severity=FindingSeverity.CRITICAL),
        ]
        sections = self._sections()
        result = ensure_critical_findings_are_surfaced(sections, findings)
        red_flags = next(s for s in result if s.title == "Red Flags")
        assert "First Critical" in red_flags.content
        assert "Second Critical" in red_flags.content
