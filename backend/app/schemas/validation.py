"""Pydantic schemas for the deterministic validation/anomaly-detection engine."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class FindingSeverity(str, Enum):
    """How serious a validation finding is. Mirrors `app.models.validation_finding.FindingSeverity`."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ValidationFindingResult(BaseModel):
    """A single finding produced by a pure validation rule function.

    This is the *pre-persistence* shape returned by
    `validation_service.run_all_validations` — deliberately without a
    `document_id` or `id`, since the same rule functions are unit-tested
    against plain `FactPoint` lists with no document context at all.
    `validation_service.persist_findings` converts these into
    `ValidationFinding` ORM rows.

    Attributes:
        severity: How serious this finding is.
        category: A short machine-readable grouping.
        title: A short, human-readable summary.
        description: A full explanation referencing the specific values
            involved.
        affected_metrics: The metric identifiers this finding concerns.
        suggested_question: A specific question to ask the company, or
            `None`.
    """

    model_config = ConfigDict(extra="forbid")

    severity: FindingSeverity
    category: str
    title: str
    description: str
    affected_metrics: list[str]
    suggested_question: str | None = None


class ValidationFindingRead(BaseModel):
    """Public representation of a persisted validation finding.

    Attributes:
        id: The finding's unique identifier.
        document_id: The document this finding applies to.
        severity: How serious this finding is.
        category: A short machine-readable grouping.
        title: A short, human-readable summary.
        description: A full explanation.
        affected_metrics: The metric identifiers this finding concerns.
        sources: Citation ids supporting this finding, if any.
        suggested_question: A specific question to ask the company, or
            `None`.
        created_at: Timestamp when this finding was recorded.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    severity: FindingSeverity
    category: str
    title: str
    description: str
    affected_metrics: list[str]
    sources: list[str]
    suggested_question: str | None
    created_at: datetime


class ValidationChecksResponse(BaseModel):
    """Response for `GET /documents/{id}/checks`.

    Attributes:
        findings: All findings for the document, most severe first.
        critical_count: Count of `CRITICAL`-severity findings.
        warning_count: Count of `WARNING`-severity findings.
        info_count: Count of `INFO`-severity findings.
    """

    findings: list[ValidationFindingRead]
    critical_count: int
    warning_count: int
    info_count: int