"""Deterministic investment scoring engine.

Computes a 0-100 investment score for a document (representing a
"company profile") from its existing `FinancialMetrics` and
`DocumentAnalysis` records. No LLM calls occur anywhere in this module
— every rule is a fixed, auditable threshold or formula over already-
extracted structured data. Services operate directly on `AsyncSession`
— there is no repository layer in this project's architecture.

Replaceability by design: all scoring logic lives behind the
`ScoringStrategy` interface. `InvestmentScoringService` depends only on
that interface, not on `DeterministicScoringStrategy` directly (beyond
using it as the default). A future ML-based strategy can implement the
same interface and be swapped in via the `strategy` parameter on
`InvestmentScoringService.calculate_score`, with no change to the
public service API, the database schema, or the HTTP endpoints.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_analysis import DocumentAnalysis
from app.models.financial_metrics import FinancialMetrics
from app.models.investment_score import InvestmentScore
from app.services.document_service import DocumentNotFoundError, DocumentService

# Weights used to combine sub-scores into `overall_score`. `team_score`
# is intentionally excluded: it is always `None` in the current data
# model (see `InvestmentScore.team_score` docstring), so it never
# participates in the weighted average. Weights for whichever of the
# remaining dimensions ARE available are renormalized to sum to 1.0.
_OVERALL_SCORE_WEIGHTS: dict[str, float] = {
    "financial_score": 0.40,
    "growth_score": 0.25,
    "risk_score": 0.25,
    "market_score": 0.10,
}

_SCORING_DIMENSIONS = (
    "financial_score",
    "growth_score",
    "risk_score",
    "market_score",
    "team_score",
)


class InvestmentScoringServiceError(Exception):
    """Base exception for investment scoring failures."""


class InsufficientDataForScoringError(InvestmentScoringServiceError):
    """Raised when a document has neither financial metrics nor a
    business analysis, leaving no data to score at all."""


@dataclass(frozen=True)
class ScoringResult:
    """The output of a scoring strategy, ready to persist.

    Attributes:
        overall_score: The weighted composite score (0-100), or `None`.
        financial_score: Financial strength sub-score, or `None`.
        growth_score: Growth trajectory sub-score, or `None`.
        risk_score: Financial stability sub-score, or `None`.
        market_score: Market-context richness sub-score, or `None`.
        team_score: Reserved team-strength sub-score, or `None`.
        confidence_score: Fraction (0.0-1.0) of dimensions computed.
        reasoning: A human-readable explanation of the score.
    """

    overall_score: float | None
    financial_score: float | None
    growth_score: float | None
    risk_score: float | None
    market_score: float | None
    team_score: float | None
    confidence_score: float | None
    reasoning: str


class ScoringStrategy(ABC):
    """Interface for computing an investment score from structured data.

    Any future scoring approach (deterministic rules, a trained ML
    model, etc.) implements this interface, which is the sole seam
    `InvestmentScoringService` depends on.
    """

    @abstractmethod
    def compute(
        self,
        financial_metrics: FinancialMetrics | None,
        analysis: DocumentAnalysis | None,
    ) -> ScoringResult:
        """Compute a score from a document's available structured data.

        Args:
            financial_metrics: The document's financial metrics, or
                `None` if none exist.
            analysis: The document's business analysis, or `None` if
                none exists.

        Returns:
            The computed `ScoringResult`.
        """


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp a value into the inclusive `[low, high]` range.

    Args:
        value: The value to clamp.
        low: The lower bound.
        high: The upper bound.

    Returns:
        The clamped value.
    """
    return max(low, min(high, value))


class DeterministicScoringStrategy(ScoringStrategy):
    """Fixed, threshold-based scoring rules over financial and analysis data.

    Every rule below is a deterministic function of already-extracted
    values — no randomness, no model inference. Thresholds are
    intentionally simple and documented inline so they are auditable and
    easy to tune.
    """

    def compute(
        self,
        financial_metrics: FinancialMetrics | None,
        analysis: DocumentAnalysis | None,
    ) -> ScoringResult:
        """Compute a deterministic investment score.

        Args:
            financial_metrics: The document's financial metrics, or
                `None`.
            analysis: The document's business analysis, or `None`.

        Returns:
            The computed `ScoringResult`.
        """
        financial_score, financial_notes = self._score_financial(financial_metrics)
        growth_score, growth_notes = self._score_growth(financial_metrics)
        risk_score, risk_notes = self._score_risk(financial_metrics)
        market_score, market_notes = self._score_market(analysis)
        team_score = None  # No team-related data exists in the current schema.

        overall_score = self._score_overall(
            financial_score, growth_score, risk_score, market_score
        )
        confidence_score = self._score_confidence(
            financial_score, growth_score, risk_score, market_score, team_score
        )
        reasoning = self._build_reasoning(
            financial_notes, growth_notes, risk_notes, market_notes
        )

        return ScoringResult(
            overall_score=overall_score,
            financial_score=financial_score,
            growth_score=growth_score,
            risk_score=risk_score,
            market_score=market_score,
            team_score=team_score,
            confidence_score=confidence_score,
            reasoning=reasoning,
        )

    def _score_financial(
        self, fm: FinancialMetrics | None
    ) -> tuple[float | None, list[str]]:
        """Score financial strength from ARR, gross margin, and EBITDA.

        Rules:
        - ARR: higher ARR bands score higher (0 if no revenue signal at
          all, up to 100 for ARR >= $10M).
        - Gross margin: higher margin bands score higher.
        - EBITDA sign: positive EBITDA adds a bonus; negative EBITDA
          applies a penalty.

        Each applicable component contributes equally to the average;
        components with no underlying value are simply excluded.

        Args:
            fm: The document's financial metrics, or `None`.

        Returns:
            A tuple of `(financial_score, reasoning_notes)`.
        """
        if fm is None:
            return None, []

        components: list[float] = []
        notes: list[str] = []

        if fm.arr is not None:
            if fm.arr >= 10_000_000:
                score = 100.0
            elif fm.arr >= 5_000_000:
                score = 85.0
            elif fm.arr >= 1_000_000:
                score = 70.0
            elif fm.arr >= 100_000:
                score = 50.0
            elif fm.arr > 0:
                score = 30.0
            else:
                score = 10.0
            components.append(score)
            notes.append(
                f"ARR of {fm.arr:,.0f}"
                f"{f' {fm.currency}' if fm.currency else ''} "
                f"contributes a financial sub-score of {score:.0f}/100."
            )

        if fm.gross_margin is not None:
            if fm.gross_margin >= 70:
                score = 100.0
            elif fm.gross_margin >= 50:
                score = 80.0
            elif fm.gross_margin >= 30:
                score = 60.0
            elif fm.gross_margin >= 0:
                score = 40.0
            else:
                score = 15.0
            components.append(score)
            notes.append(
                f"Gross margin of {fm.gross_margin:.1f}% contributes "
                f"a financial sub-score of {score:.0f}/100."
            )

        if fm.ebitda is not None:
            score = 65.0 if fm.ebitda >= 0 else 30.0
            components.append(score)
            notes.append(
                f"{'Positive' if fm.ebitda >= 0 else 'Negative'} EBITDA of "
                f"{fm.ebitda:,.0f} "
                f"{'supports' if fm.ebitda >= 0 else 'weighs on'} the "
                f"financial score."
            )

        if not components:
            return None, []

        return round(sum(components) / len(components), 1), notes

    def _score_growth(
        self, fm: FinancialMetrics | None
    ) -> tuple[float | None, list[str]]:
        """Score growth trajectory from the growth rate.

        Rules: higher, positive growth rates score higher; negative
        growth rates score progressively lower the more negative they
        are.

        Args:
            fm: The document's financial metrics, or `None`.

        Returns:
            A tuple of `(growth_score, reasoning_notes)`.
        """
        if fm is None or fm.growth_rate is None:
            return None, []

        rate = fm.growth_rate
        if rate >= 50:
            score = 100.0
        elif rate >= 25:
            score = 85.0
        elif rate >= 10:
            score = 70.0
        elif rate >= 0:
            score = 55.0
        elif rate >= -10:
            score = 35.0
        else:
            score = 15.0

        notes = [
            f"Growth rate of {rate:.1f}% yields a growth score of {score:.0f}/100."
        ]
        return score, notes

    def _score_risk(
        self, fm: FinancialMetrics | None
    ) -> tuple[float | None, list[str]]:
        """Score financial stability from runway and burn rate.

        Higher is always safer. Rules:
        - Runway: longer runway scores higher.
        - Burn relative to revenue (when both are known): a lower
          burn/revenue ratio scores higher, since burn is being offset
          by real revenue.

        Args:
            fm: The document's financial metrics, or `None`.

        Returns:
            A tuple of `(risk_score, reasoning_notes)`.
        """
        if fm is None:
            return None, []

        components: list[float] = []
        notes: list[str] = []

        if fm.runway_months is not None:
            if fm.runway_months >= 18:
                score = 100.0
            elif fm.runway_months >= 12:
                score = 80.0
            elif fm.runway_months >= 6:
                score = 55.0
            elif fm.runway_months >= 3:
                score = 30.0
            else:
                score = 10.0
            components.append(score)
            notes.append(
                f"Runway of {fm.runway_months:.1f} months contributes a "
                f"risk (stability) sub-score of {score:.0f}/100."
            )

        if fm.burn_rate is not None and fm.revenue:
            ratio = fm.burn_rate / fm.revenue
            if ratio <= 0.25:
                score = 90.0
            elif ratio <= 0.5:
                score = 70.0
            elif ratio <= 1.0:
                score = 45.0
            else:
                score = 20.0
            components.append(score)
            notes.append(
                f"Monthly burn relative to revenue ({ratio:.2f}x) "
                f"contributes a risk sub-score of {score:.0f}/100."
            )

        if not components:
            return None, []

        return round(sum(components) / len(components), 1), notes

    def _score_market(
        self, analysis: DocumentAnalysis | None
    ) -> tuple[float | None, list[str]]:
        """Score market-context richness from identified analysis fields.

        This is a data-completeness heuristic, not a judgment of actual
        market attractiveness: it reflects how much market context
        (industry, customer segments, competitors, revenue streams) the
        business analysis was able to identify, on the premise that a
        well-documented market position carries less unknown risk than
        an undocumented one.

        Args:
            analysis: The document's business analysis, or `None`.

        Returns:
            A tuple of `(market_score, reasoning_notes)`.
        """
        if analysis is None:
            return None, []

        signals = [
            bool(analysis.industry),
            bool(analysis.customers),
            bool(analysis.competitors),
            bool(analysis.revenue_streams),
        ]
        populated = sum(signals)
        score = round((populated / len(signals)) * 100, 1)

        notes = [
            f"Market context is documented across {populated}/{len(signals)} "
            f"identified dimensions (industry, customers, competitors, "
            f"revenue streams), yielding a market score of {score:.0f}/100."
        ]
        return score, notes

    def _score_overall(
        self,
        financial_score: float | None,
        growth_score: float | None,
        risk_score: float | None,
        market_score: float | None,
    ) -> float | None:
        """Combine sub-scores into a weighted overall score.

        Weights for whichever sub-scores are available are renormalized
        to sum to 1.0, so a document missing some dimensions is not
        penalized simply for missing data in the overall figure — the
        reduced confidence in `confidence_score` communicates that
        instead.

        Args:
            financial_score: The financial sub-score, or `None`.
            growth_score: The growth sub-score, or `None`.
            risk_score: The risk sub-score, or `None`.
            market_score: The market sub-score, or `None`.

        Returns:
            The weighted overall score, or `None` if no sub-scores are
            available at all.
        """
        available = {
            "financial_score": financial_score,
            "growth_score": growth_score,
            "risk_score": risk_score,
            "market_score": market_score,
        }
        present = {k: v for k, v in available.items() if v is not None}

        if not present:
            return None

        weight_sum = sum(_OVERALL_SCORE_WEIGHTS[k] for k in present)
        weighted_total = sum(
            present[k] * _OVERALL_SCORE_WEIGHTS[k] for k in present
        )
        return round(_clamp(weighted_total / weight_sum), 1)

    def _score_confidence(
        self,
        financial_score: float | None,
        growth_score: float | None,
        risk_score: float | None,
        market_score: float | None,
        team_score: float | None,
    ) -> float:
        """Compute confidence as the fraction of scoring dimensions available.

        `team_score` is always `None` in the current data model, so the
        maximum achievable confidence today is 0.8 (4 of 5 dimensions).
        This will rise automatically once a team-data source populates
        `team_score`, with no change to this method.

        Args:
            financial_score: The financial sub-score, or `None`.
            growth_score: The growth sub-score, or `None`.
            risk_score: The risk sub-score, or `None`.
            market_score: The market sub-score, or `None`.
            team_score: The team sub-score, or `None`.

        Returns:
            A confidence fraction between 0.0 and 1.0.
        """
        scores = [financial_score, growth_score, risk_score, market_score, team_score]
        available = sum(1 for s in scores if s is not None)
        return round(available / len(scores), 2)

    def _build_reasoning(
        self,
        financial_notes: list[str],
        growth_notes: list[str],
        risk_notes: list[str],
        market_notes: list[str],
    ) -> str:
        """Assemble a human-readable explanation from per-dimension notes.

        Built entirely from the structured notes generated while scoring
        each dimension — no free-form generation, no LLM involvement.

        Args:
            financial_notes: Notes from `_score_financial`.
            growth_notes: Notes from `_score_growth`.
            risk_notes: Notes from `_score_risk`.
            market_notes: Notes from `_score_market`.

        Returns:
            The assembled reasoning text.
        """
        all_notes = financial_notes + growth_notes + risk_notes + market_notes

        if not all_notes:
            return (
                "No financial metrics or business analysis were available "
                "for this document, so no score components could be computed."
            )

        notes_text = " ".join(all_notes)
        return (
            f"{notes_text} Team strength could not be assessed, as no "
            f"team-related data is currently captured for this document."
        )


_default_strategy = DeterministicScoringStrategy()


async def _fetch_analysis(
    db: AsyncSession, document_id: uuid.UUID
) -> DocumentAnalysis | None:
    """Fetch a document's business analysis, if one exists.

    Queries directly rather than through `DocumentAnalysisService`,
    since organization-membership access control has already been
    enforced by the caller via `DocumentService.get_document` — a
    second membership check here would be redundant.

    Args:
        db: The active database session.
        document_id: The document's id.

    Returns:
        The `DocumentAnalysis` if found, otherwise `None`.
    """
    result = await db.execute(
        select(DocumentAnalysis).where(DocumentAnalysis.document_id == document_id)
    )
    return result.scalar_one_or_none()


async def _fetch_financial_metrics(
    db: AsyncSession, document_id: uuid.UUID
) -> FinancialMetrics | None:
    """Fetch a document's financial metrics, if any exist.

    Args:
        db: The active database session.
        document_id: The document's id.

    Returns:
        The `FinancialMetrics` if found, otherwise `None`.
    """
    result = await db.execute(
        select(FinancialMetrics).where(FinancialMetrics.document_id == document_id)
    )
    return result.scalar_one_or_none()


async def _fetch_existing_score(
    db: AsyncSession, document_id: uuid.UUID
) -> InvestmentScore | None:
    """Fetch a document's existing score row, if one exists.

    Args:
        db: The active database session.
        document_id: The document's id.

    Returns:
        The `InvestmentScore` if found, otherwise `None`.
    """
    result = await db.execute(
        select(InvestmentScore).where(InvestmentScore.document_id == document_id)
    )
    return result.scalar_one_or_none()


class InvestmentScoreNotFoundError(InvestmentScoringServiceError):
    """Raised when a document has not yet had a score calculated."""


class InvestmentScoringService:
    """Use cases for calculating and retrieving document investment scores."""

    @staticmethod
    async def calculate_score(
        db: AsyncSession,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
        strategy: ScoringStrategy | None = None,
    ) -> InvestmentScore:
        """Calculate (or recalculate) a document's investment score.

        Loads the document's financial metrics and business analysis in
        two direct queries, computes a score via `strategy`, and
        persists the result. If the document already has a score, it is
        overwritten in place.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the user requesting scoring.
            strategy: The scoring strategy to use. Defaults to
                `DeterministicScoringStrategy`. Accepting this as a
                parameter (rather than hardcoding the strategy) is what
                allows a future ML-based strategy to be substituted
                without changing this method's signature or callers.

        Returns:
            The newly created or updated `InvestmentScore`.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization.
            InsufficientDataForScoringError: If the document has neither
                financial metrics nor a business analysis.
        """
        strategy = strategy or _default_strategy

        await DocumentService.get_document(db, document_id, actor_id)

        financial_metrics = await _fetch_financial_metrics(db, document_id)
        analysis = await _fetch_analysis(db, document_id)

        if financial_metrics is None and analysis is None:
            raise InsufficientDataForScoringError(
                "This document has neither financial metrics nor a "
                "business analysis. Run POST /documents/{id}/analyze "
                "and/or POST /documents/{id}/financial-analysis first."
            )

        result = strategy.compute(financial_metrics, analysis)

        existing = await _fetch_existing_score(db, document_id)

        if existing is not None:
            existing.overall_score = result.overall_score
            existing.financial_score = result.financial_score
            existing.growth_score = result.growth_score
            existing.risk_score = result.risk_score
            existing.market_score = result.market_score
            existing.team_score = result.team_score
            existing.confidence_score = result.confidence_score
            existing.reasoning = result.reasoning
            score = existing
        else:
            score = InvestmentScore(
                document_id=document_id,
                overall_score=result.overall_score,
                financial_score=result.financial_score,
                growth_score=result.growth_score,
                risk_score=result.risk_score,
                market_score=result.market_score,
                team_score=result.team_score,
                confidence_score=result.confidence_score,
                reasoning=result.reasoning,
            )
            db.add(score)

        await db.commit()
        await db.refresh(score)
        return score

    @staticmethod
    async def get_score(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> InvestmentScore:
        """Fetch a document's existing investment score.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.

        Returns:
            The document's `InvestmentScore`.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization.
            InvestmentScoreNotFoundError: If the document has not yet
                been scored.
        """
        await DocumentService.get_document(db, document_id, actor_id)

        score = await _fetch_existing_score(db, document_id)
        if score is None:
            raise InvestmentScoreNotFoundError(
                "This document has not been scored yet."
            )

        return score