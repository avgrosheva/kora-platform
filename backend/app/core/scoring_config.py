"""Versioned configuration for the deterministic investment scoring engine.

Weights and version live here, separate from the scoring logic itself,
so tuning them (or introducing a new methodology version) never
requires touching `investment_scoring_service.py`'s calculation code —
only this config. `InvestmentScore.methodology_version` records which
version of this config produced a given score, for auditability.
"""

SCORING_METHODOLOGY_VERSION = "kora_score_v2"

SCORE_WEIGHTS: dict[str, float] = {
    "financial_score": 0.40,
    "growth_score": 0.25,
    "risk_score": 0.25,
    "market_score": 0.10,
}