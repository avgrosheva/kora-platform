"""Pydantic schemas for the missing-information checklist framework."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class FieldStatus(str, Enum):
    """The status of a single checklist field. Mirrors
    `app.models.missing_information_item.FieldStatus`."""

    FOUND = "found"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    CONTRADICTORY = "contradictory"
    NOT_APPLICABLE = "not_applicable"


class ChecklistItemResult(BaseModel):
    """A single checklist field's computed status.

    Attributes:
        category: The checklist category (e.g. `"financial"`, `"team"`).
        field_name: The specific field within that category.
        status: Whether this field was found, missing, ambiguous,
            contradictory, or not applicable.
    """

    model_config = ConfigDict(extra="forbid")

    category: str
    field_name: str
    status: FieldStatus


class MissingInformationByCategory(BaseModel):
    """Missing/ambiguous/contradictory fields grouped by category.

    Attributes:
        category: The checklist category.
        missing: Field names with status `MISSING`.
        ambiguous: Field names with status `AMBIGUOUS`.
        contradictory: Field names with status `CONTRADICTORY`.
    """

    category: str
    missing: list[str]
    ambiguous: list[str]
    contradictory: list[str]


class MissingInformationResponse(BaseModel):
    """Response for the missing-information checklist.

    Attributes:
        items: Every checklist item's computed status, unfiltered.
        by_category: Missing/ambiguous/contradictory fields grouped by
            category, for direct UI rendering (matches Section 7's
            due-diligence "group missing data by category" requirement).
        total_required: Total number of checklist fields evaluated.
        total_found: Number of fields with status `FOUND`.
    """

    items: list[ChecklistItemResult]
    by_category: list[MissingInformationByCategory]
    total_required: int
    total_found: int