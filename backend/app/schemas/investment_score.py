"""Pydantic schemas for deterministic investment scores."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.investment_score import AssessmentStatus


class CategoryBreakdownEntry(BaseModel):
    """One dimension's entry in `InvestmentScoreRead.category_breakdown`.

    Mirrors exactly what `investment_scoring_service._build_category_breakdown`
    produces for one scoring dimension.

    Attributes:
        status: `"assessed"` if this dimension had data to score,
            `"not_assessable"` otherwise.
        score: The dimension's 0-100 sub-score, or `None` if
            `not_assessable`.
        weight: The dimension's configured weight (see
            `app.core.scoring_config.SCORE_WEIGHTS`), regardless of
            whether it was assessable.
        contribution: This dimension's contribution to `overall_score`
            (its score times its renormalized weight), or `None` if
            `not_assessable` or if `overall_score` itself is `None`
            (Step 8: `INSUFFICIENT_EVIDENCE`).
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["assessed", "not_assessable"]
    score: float | None
    weight: float
    contribution: float | None


class InvestmentScoreRead(BaseModel):
    """Public representation of a document's investment score.

    Attributes:
        id: The score record's unique identifier.
        document_id: The scored document's id.
        overall_score: The weighted composite score (0-100), or `None`
            — either because no sub-scores were computable at all, or
            because `assessment_status` is `INSUFFICIENT_EVIDENCE`
            (Step 8). Callers must not treat a `None` here as a low
            score; it means no single number is being asserted.
        financial_score: Financial strength sub-score (0-100), or
            `None`.
        growth_score: Growth trajectory sub-score (0-100), or `None`.
        risk_score: Financial stability sub-score (0-100, higher is
            safer), or `None`.
        market_score: Market-context richness sub-score (0-100), or
            `None`.
        team_score: Reserved for a future team-strength signal. Always
            `None` in the current data model.
        confidence_score: Fraction (0.0-1.0) of scoring dimensions that
            could be computed.
        reasoning: A human-readable, non-AI-generated explanation of
            the score.
        assessment_status: Whether enough evidence exists to present
            `overall_score` as a single number. `None` for score records
            calculated before Step 8 shipped, until the next recalculation.
        methodology_version: The scoring methodology version that
            produced this record.
        category_breakdown: Per-dimension score/weight/contribution
            detail, keyed by dimension name (e.g. `"financial_score"`).
        created_at: Timestamp when the score was first created.
        updated_at: Timestamp when the score was last recalculated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    overall_score: float | None
    financial_score: float | None
    growth_score: float | None
    risk_score: float | None
    market_score: float | None
    team_score: float | None
    confidence_score: float | None
    reasoning: str | None
    assessment_status: AssessmentStatus | None
    methodology_version: str | None
    category_breakdown: dict[str, CategoryBreakdownEntry] | None
    created_at: datetime
    updated_at: datetime


class InvestmentScoreResponse(InvestmentScoreRead):
    """API response for score calculation and retrieval endpoints.

    Currently identical to `InvestmentScoreRead`; kept as a distinct
    type so the endpoint's response contract can evolve independently
    (e.g. to include a version tag once an ML-based strategy is
    introduced) without affecting other reads of the same data.
    """