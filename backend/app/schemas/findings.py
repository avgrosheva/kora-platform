"""Pydantic schemas for the unified findings facade (`findings_service.py`).

Defines its own `FindingType`/`FindingSeverity` enums rather than
importing `findings_service.py`'s, matching this project's established
convention that `app/schemas/*` never imports from `app/services/*` (the
dependency only ever runs the other way). The API layer is responsible
for converting a `findings_service.Finding` into a `FindingRead` — see
`app/api/v1/documents.py`'s `_finding_to_read`.
"""

import uuid
from enum import Enum

from pydantic import BaseModel, ConfigDict


class FindingType(str, Enum):
    """Mirrors `findings_service.FindingType` — see there for what each
    value means and why the distinction matters."""

    DETERMINISTIC = "deterministic"
    DOCUMENT_STATED = "document_stated"
    DERIVED = "derived"
    AI_INFERRED = "ai_inferred"


class FindingSeverity(str, Enum):
    """Mirrors `findings_service.FindingSeverity`."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class FindingRead(BaseModel):
    """Public representation of one unified finding.

    Attributes:
        title: A short, human-readable summary. For `AI_INFERRED`
            findings, always includes a plain-text "(Kora-inferred)"
            marker — see `findings_service.py`'s module docstring for
            why this is required in addition to `type`.
        category: A short, machine-readable grouping.
        severity: How serious this finding is.
        type: Where this finding came from — deterministic check,
            document-stated claim, derived, or Kora's own inference.
            Any display of a finding MUST branch on this field: an
            `AI_INFERRED` finding must never be presented the same way
            as a `DOCUMENT_STATED` one.
        evidence: The concrete data point this finding rests on, or
            `None`.
        explanation: Why this matters, or `None`.
        implication: The reasoned consequence for an investor, or
            `None` — only ever populated for `AI_INFERRED` findings.
        recommended_next_step: A concrete question or action, or `None`.
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    category: str
    severity: FindingSeverity
    type: FindingType
    evidence: str | None
    explanation: str | None
    implication: str | None
    recommended_next_step: str | None


class FindingsResponse(BaseModel):
    """A document's complete set of unified findings, with counts by
    severity and by type — so a client can distinguish "checked and
    clean" from "nothing checked yet" without inspecting every finding
    itself (Evidence Layer plan, Step 7).

    Attributes:
        document_id: The document's id.
        findings: Every finding, in the order `FindingsService.get_findings`
            produced them (deterministic, then document-stated, then
            ai-inferred; each group ordered as its source produced it).
        critical_count: Number of `CRITICAL` severity findings.
        high_count: Number of `HIGH` severity findings.
        medium_count: Number of `MEDIUM` severity findings.
        low_count: Number of `LOW` severity findings.
        informational_count: Number of `INFORMATIONAL` severity findings.
        deterministic_count: Number of `DETERMINISTIC` type findings —
            i.e. how many of `validation_service.py`'s rules fired.
        document_stated_count: Number of `DOCUMENT_STATED` type findings
            — i.e. how many extracted qualitative facts were risk claims.
        ai_inferred_count: Number of `AI_INFERRED` type findings.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID
    findings: list[FindingRead]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    informational_count: int
    deterministic_count: int
    document_stated_count: int
    ai_inferred_count: int
