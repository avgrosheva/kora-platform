"""Pydantic schemas for deterministic investment scores."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InvestmentScoreRead(BaseModel):
    """Public representation of a document's investment score.

    Attributes:
        id: The score record's unique identifier.
        document_id: The scored document's id.
        overall_score: The weighted composite score (0-100), or `None`.
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
    created_at: datetime
    updated_at: datetime


class InvestmentScoreResponse(InvestmentScoreRead):
    """API response for score calculation and retrieval endpoints.

    Currently identical to `InvestmentScoreRead`; kept as a distinct
    type so the endpoint's response contract can evolve independently
    (e.g. to include a version tag once an ML-based strategy is
    introduced) without affecting other reads of the same data.
    """