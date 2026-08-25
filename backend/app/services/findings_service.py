"""Unified findings facade (Step 5 of the Evidence Layer plan).

Today, "what's wrong or worth flagging about this document" is answered
in different, disconnected ways depending on which screen is asking:
Checks reads `ValidationFinding` rows; the due-diligence report and
Checks tab separately read `DocumentAnalysis.risks` as an undifferentiated
free-text list; nothing reads `qualitative_facts` at all. This is the
root cause of Bug C (the generated report can say "no red flags" in the
same response where structured red-flag data exists) — different
features never look at the same assembled picture.

`FindingsService` is the single facade every other service should call
to answer "what are this document's findings" from now on. It does not
replace any of the three sources it wraps — it normalizes their output
into one `Finding` shape:

1. **Deterministic** (`FindingType.DETERMINISTIC`) — wraps `ValidationFinding`
   rows exactly as `validation_service.py`'s rule engine already produces
   them. That engine (and its persistence) is untouched; only
   `ValidationService.list_findings`, a plain read accessor, was added.
2. **Document-stated** (`FindingType.DOCUMENT_STATED`) — wraps `QualitativeFact`
   rows that carry a `severity_hint`. Per the Step 4 extraction prompt, a
   `severity_hint` is only ever set for a genuine risk-shaped claim —
   `OPPORTUNITY` claims and anything else with no risk dimension are
   `None` and are correctly excluded here; they are not findings.
3. **AI-inferred** (`FindingType.AI_INFERRED`) — a small, fixed set of
   deterministic Python rules (never an LLM call at query time) that draw
   out a consequence beyond what a `QualitativeFact` literally states —
   e.g. an `OPERATIONAL_DEPENDENCY` claim implies concentration risk that
   the document itself never says in those words. These are always
   labeled `AI_INFERRED` (via `Finding.type`) and their `title` also
   spells out "(Kora-inferred)" in plain text, so no future display
   surface can present one as a verified document fact just by forgetting
   to branch on `type`.

Coverage, Score, Report, and Chat are deliberately NOT rewired to this
facade in this step — that is Step 6 (Report) and Step 10 (Chat) of the
plan. This step only builds the facade and proves it works in isolation.
No Pydantic/API schema is added here either, since there is no endpoint
yet to expose it through; `Finding`'s explicit `type` field is the shape
a future schema should mirror 1:1.
"""

import enum
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qualitative_fact import QualitativeFact, QualitativeFactCategory
from app.models.validation_finding import ValidationFinding
from app.schemas.validation import FindingSeverity as ValidationFindingSeverity
from app.services.qualitative_facts_service import QualitativeFactsService
from app.services.validation_service import ValidationService


class FindingType(str, enum.Enum):
    """Where a `Finding` came from, and therefore how much to trust it
    as a verified fact versus Kora's own conclusion.

    Attributes:
        DETERMINISTIC: A `validation_service.py` rule — pure arithmetic
            or cross-field consistency logic, never an LLM.
        DOCUMENT_STATED: A `QualitativeFact` the AI extracted directly
            from the document, with a citation behind it.
        DERIVED: Reserved, unused by this step. Mirrors
            `EvidenceFactType.DERIVED`/`FinancialValueType.DERIVED` for a
            future finding computed from other facts (e.g. a `DerivedMetric`
            crossing a threshold) rather than either a deterministic rule
            or a document-stated claim.
        AI_INFERRED: One of this module's own inference rules. Must
            always be visibly labeled as such wherever displayed — never
            presented as a verified fact or something the document
            itself states.
    """

    DETERMINISTIC = "deterministic"
    DOCUMENT_STATED = "document_stated"
    DERIVED = "derived"
    AI_INFERRED = "ai_inferred"


class FindingSeverity(str, enum.Enum):
    """How serious a finding is, on the same five-level scale as
    `QualitativeFactSeverityHint` (kept as a separate enum, not a direct
    reuse, so `Finding`'s public shape doesn't silently change if that
    model-layer enum ever does — see `evidence_service.EvidenceFactType`
    for the same precedent).
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass(frozen=True)
class Finding:
    """One normalized finding, regardless of which source produced it.

    Attributes:
        title: A short, human-readable summary. For `AI_INFERRED`
            findings, always includes a plain-text "(Kora-inferred)"
            marker in addition to `type` — defense in depth against a
            future display surface that forgets to branch on `type`.
        category: A short, machine-readable grouping. For deterministic
            findings, `ValidationFinding.category` (e.g.
            `"financial_consistency"`); for document-stated and
            ai-inferred findings, the underlying `QualitativeFactCategory`
            value (e.g. `"operational_dependency"`).
        severity: How serious this finding is.
        type: Where this finding came from (see `FindingType`) — the
            field that must always be checked before deciding how to
            present a finding to a user.
        evidence: The concrete data point this finding rests on (e.g.
            the affected metric names, or the qualitative fact's claim
            text), or `None` if not applicable.
        explanation: Why this matters, or `None` if the source doesn't
            provide one (a document-stated finding's `evidence` already
            *is* its own explanation — the document's own words — so
            fabricating a separate one here would add unsupported text).
        implication: The reasoned consequence for an investor, or `None`.
            Only ever populated for `AI_INFERRED` findings — an
            `implication` is itself a step beyond what a document states
            or a deterministic rule computes, so attaching one to a
            `DOCUMENT_STATED` finding would blur exactly the "document
            says vs. Kora concludes" line this whole layer exists to keep
            visible.
        recommended_next_step: A concrete question or action, or `None`
            if the source doesn't provide one. Deterministic findings use
            `ValidationFinding.suggested_question` directly;
            document-stated findings leave this `None` (generating one
            generically, without referencing the claim's specifics, is
            Step 9's job — "Rewrite founder-question generation" — not
            this step's).
    """

    title: str
    category: str
    severity: FindingSeverity
    type: FindingType
    evidence: str | None
    explanation: str | None
    implication: str | None
    recommended_next_step: str | None


# ---------------------------------------------------------------------------
# 1. Deterministic findings — wraps ValidationFinding as-is
# ---------------------------------------------------------------------------

# ValidationFinding's severity is a 3-level scale (info/warning/critical);
# Finding's is 5-level. "warning" maps to the middle of the 5-level scale
# rather than being arbitrarily called "high" or "low" -- the 3-level
# source genuinely doesn't distinguish those, and inventing that
# distinction here would overclaim precision the source doesn't have.
_VALIDATION_SEVERITY_TO_FINDING_SEVERITY: dict[str, FindingSeverity] = {
    ValidationFindingSeverity.INFO.value: FindingSeverity.INFORMATIONAL,
    ValidationFindingSeverity.WARNING.value: FindingSeverity.MEDIUM,
    ValidationFindingSeverity.CRITICAL.value: FindingSeverity.CRITICAL,
}


def findings_from_validation(findings: list[ValidationFinding]) -> list[Finding]:
    """Wrap `ValidationFinding` rows into the unified `Finding` shape.

    Args:
        findings: The document's persisted validation findings, as
            returned by `ValidationService.list_findings`.

    Returns:
        One `Finding` per input row, always `FindingType.DETERMINISTIC`.
    """
    return [
        Finding(
            title=finding.title,
            category=finding.category,
            severity=_VALIDATION_SEVERITY_TO_FINDING_SEVERITY.get(finding.severity, FindingSeverity.MEDIUM),
            type=FindingType.DETERMINISTIC,
            evidence=", ".join(finding.affected_metrics) if finding.affected_metrics else None,
            explanation=finding.description,
            implication=None,
            recommended_next_step=finding.suggested_question,
        )
        for finding in findings
    ]


# ---------------------------------------------------------------------------
# 2. Document-stated findings — wraps QualitativeFact risk claims
# ---------------------------------------------------------------------------

_QUALITATIVE_SEVERITY_TO_FINDING_SEVERITY: dict[str, FindingSeverity] = {
    "critical": FindingSeverity.CRITICAL,
    "high": FindingSeverity.HIGH,
    "medium": FindingSeverity.MEDIUM,
    "low": FindingSeverity.LOW,
    "informational": FindingSeverity.INFORMATIONAL,
}

_CATEGORY_TITLE: dict[str, str] = {
    QualitativeFactCategory.CUSTOMER_RISK.value: "Customer Risk",
    QualitativeFactCategory.LEGAL_REGULATORY.value: "Legal / Regulatory Risk",
    QualitativeFactCategory.OPERATIONAL_DEPENDENCY.value: "Operational Dependency",
    QualitativeFactCategory.IP_OWNERSHIP.value: "IP Ownership Risk",
    QualitativeFactCategory.TEAM_RISK.value: "Team Risk",
    QualitativeFactCategory.MARKET_RISK.value: "Market Risk",
    QualitativeFactCategory.OPPORTUNITY.value: "Opportunity",
    QualitativeFactCategory.OTHER.value: "Other",
}


def findings_from_qualitative_risks(facts: list[QualitativeFact]) -> list[Finding]:
    """Wrap risk-shaped `QualitativeFact` rows into `Finding`s.

    A fact with `severity_hint=None` is not a risk claim (per the Step 4
    extraction prompt, that's reserved for `OPPORTUNITY` claims and
    anything else with no risk dimension) and is excluded — this
    function only ever returns risk findings, matching the plan's
    "qualitative_facts, flagged as risks" wording exactly.

    Args:
        facts: The document's qualitative facts, as returned by
            `QualitativeFactsService.list_facts`.

    Returns:
        One `Finding` per risk-shaped fact, always
        `FindingType.DOCUMENT_STATED`.
    """
    return [
        Finding(
            title=_CATEGORY_TITLE.get(fact.category, fact.category),
            category=fact.category,
            severity=_QUALITATIVE_SEVERITY_TO_FINDING_SEVERITY.get(fact.severity_hint, FindingSeverity.MEDIUM),
            type=FindingType.DOCUMENT_STATED,
            evidence=fact.claim_text,
            explanation=None,
            implication=None,
            recommended_next_step=None,
        )
        for fact in facts
        if fact.severity_hint is not None
    ]


# ---------------------------------------------------------------------------
# 3. AI-inferred findings — a small, fixed set of deterministic rules
# ---------------------------------------------------------------------------
#
# Each rule is a pure function over QualitativeFacts, keyed only on
# category -- never on any specific company, product, or document, per
# the plan's explicit constraint not to hardcode logic against a specific
# test document. Adding a rule means adding one function and registering
# it in _INFERENCE_RULES; nothing else in this module needs to change.


def _infer_operational_concentration_risk(facts: list[QualitativeFact]) -> list[Finding]:
    """A dependency on a single vendor/provider/process implies
    concentration risk beyond what the claim itself states."""
    return [
        Finding(
            title="Operational Concentration Risk (Kora-inferred)",
            category=QualitativeFactCategory.OPERATIONAL_DEPENDENCY.value,
            severity=_QUALITATIVE_SEVERITY_TO_FINDING_SEVERITY.get(fact.severity_hint, FindingSeverity.MEDIUM),
            type=FindingType.AI_INFERRED,
            evidence=f'Document states: "{fact.claim_text}"',
            explanation=(
                "A dependency on a single vendor, provider, or process is a "
                "concentration risk: if that relationship is disrupted, "
                "terminated, or renegotiated on worse terms, the business has "
                "no immediate alternative in place."
            ),
            implication=(
                "Operational continuity is not fully within the company's own "
                "control while this dependency exists."
            ),
            recommended_next_step=(
                "Ask whether a contingency plan or alternative provider exists, "
                "and what switching would cost in time and money."
            ),
        )
        for fact in facts
        if fact.category == QualitativeFactCategory.OPERATIONAL_DEPENDENCY.value
    ]


def _infer_ip_ownership_diligence_risk(facts: list[QualitativeFact]) -> list[Finding]:
    """An IP ownership question implies a diligence risk to the
    investment's own legal footing, beyond the claim itself."""
    return [
        Finding(
            title="IP Ownership Diligence Risk (Kora-inferred)",
            category=QualitativeFactCategory.IP_OWNERSHIP.value,
            severity=_QUALITATIVE_SEVERITY_TO_FINDING_SEVERITY.get(fact.severity_hint, FindingSeverity.MEDIUM),
            type=FindingType.AI_INFERRED,
            evidence=f'Document states: "{fact.claim_text}"',
            explanation=(
                "If intellectual property is not clearly and fully assigned to "
                "the company itself, the value being invested in may not be "
                "the company's alone to sell, license, or defend."
            ),
            implication=(
                "An investor's economic interest could be undermined by an "
                "unresolved third-party IP claim."
            ),
            recommended_next_step=(
                "Request IP assignment agreements confirming the company holds "
                "clear title to the intellectual property referenced."
            ),
        )
        for fact in facts
        if fact.category == QualitativeFactCategory.IP_OWNERSHIP.value
    ]


def _infer_team_continuity_risk(facts: list[QualitativeFact]) -> list[Finding]:
    """A team-risk claim implies an execution-continuity risk beyond
    the claim itself."""
    return [
        Finding(
            title="Team Continuity Risk (Kora-inferred)",
            category=QualitativeFactCategory.TEAM_RISK.value,
            severity=_QUALITATIVE_SEVERITY_TO_FINDING_SEVERITY.get(fact.severity_hint, FindingSeverity.MEDIUM),
            type=FindingType.AI_INFERRED,
            evidence=f'Document states: "{fact.claim_text}"',
            explanation=(
                "A team-related risk can threaten execution continuity if the "
                "people or processes involved are not readily replaceable."
            ),
            implication=(
                "Near-term execution may depend more on specific individuals "
                "than on institutionalized process."
            ),
            recommended_next_step=(
                "Ask what succession plan or redundancy exists for the roles "
                "or people this risk concerns."
            ),
        )
        for fact in facts
        if fact.category == QualitativeFactCategory.TEAM_RISK.value
    ]


_INFERENCE_RULES = (
    _infer_operational_concentration_risk,
    _infer_ip_ownership_diligence_risk,
    _infer_team_continuity_risk,
)


def run_inference_rules(facts: list[QualitativeFact]) -> list[Finding]:
    """Run every registered inference rule over a document's qualitative facts.

    Args:
        facts: The document's qualitative facts.

    Returns:
        All `AI_INFERRED` findings every rule produced, in registration
        order. A fact can trigger more than one rule in principle (none
        of today's three rules overlap in category, so in practice each
        fact triggers at most one), and a rule that finds nothing simply
        contributes no findings.
    """
    findings: list[Finding] = []
    for rule in _INFERENCE_RULES:
        findings.extend(rule(facts))
    return findings


# ---------------------------------------------------------------------------
# DB-facing facade
# ---------------------------------------------------------------------------


class FindingsService:
    """The facade other services should use to answer "what are this
    document's findings?" — deterministic checks, document-stated risks,
    and Kora's own inferences, in one list.
    """

    @staticmethod
    async def get_findings(db: AsyncSession, document_id: uuid.UUID) -> list[Finding]:
        """Fetch and normalize every finding for a document.

        Args:
            db: The active database session.
            document_id: The document's id.

        Returns:
            All findings: wrapped `ValidationFinding` rows, wrapped
            risk-shaped `QualitativeFact` rows, and every `AI_INFERRED`
            finding the inference rules produce from those same
            qualitative facts. Empty if the document has neither
            validation findings nor qualitative facts yet.
        """
        validation_findings = await ValidationService.list_findings(db, document_id)
        qualitative_facts = await QualitativeFactsService.list_facts(db, document_id)

        findings: list[Finding] = []
        findings.extend(findings_from_validation(validation_findings))
        findings.extend(findings_from_qualitative_risks(qualitative_facts))
        findings.extend(run_inference_rules(qualitative_facts))
        return findings
