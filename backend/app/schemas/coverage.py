"""Pydantic schemas for the explainable coverage/confidence assessment."""

from pydantic import BaseModel, ConfigDict


class CategoryCoverage(BaseModel):
    """Coverage for a single checklist category.

    Attributes:
        found: The number of required fields found for this category.
        required: The total number of required fields for this
            category.
        score: `found / required`, or `0.0` if `required` is `0`.
    """

    found: int
    required: int
    score: float


class CoverageAssessmentResult(BaseModel):
    """The pre-persistence result of a coverage computation.

    Attributes:
        overall_confidence: A composite 0.0-1.0 score, computed as the
            average of all category scores. Never an investment-quality
            signal — see `coverage_service.py`'s module docstring.
        coverage: Per-category coverage.
        source_coverage: Fraction of found fields that have a citation.
        ambiguities_count: Number of fields with multiple candidates.
        critical_missing_fields: Missing fields flagged as critical.
    """

    overall_confidence: float
    coverage: dict[str, CategoryCoverage]
    source_coverage: float
    ambiguities_count: int
    critical_missing_fields: list[str]


class CoverageAssessmentRead(CoverageAssessmentResult):
    """Public representation of a persisted coverage assessment.

    Attributes:
        document_id: The document this assessment covers.
    """

    model_config = ConfigDict(from_attributes=True)

    document_id: str