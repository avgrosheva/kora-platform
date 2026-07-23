"""Financial intelligence orchestration.

Converts a document's persisted `DocumentAnalysis` (and underlying text)
into structured financial KPIs via `AIService`, normalizes the raw
extraction, computes derived metrics, and persists the result. Services
operate directly on `AsyncSession` — there is no repository layer in
this project's architecture.

Design note on data types: `FinancialMetrics` stores all figures as
plain floats rather than `Decimal`. This is a deliberate choice for this
layer — these are AI-extracted, approximate business intelligence
figures for dashboards and trend analysis, not accounting-grade ledger
entries. Floats serialize directly to JSON with no additional
transformation, which is what "future compatibility" with dashboard
endpoints requires.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_metrics import FinancialMetrics
from app.schemas.financial_metrics import FinancialMetricsCreate
from app.services.ai_service import AIService, FinancialExtractionResult
from app.services.document_analysis_service import (
    AnalysisNotFoundError,
    DocumentAnalysisService,
)
from app.services.document_service import DocumentNotFoundError, DocumentService

_EXTRACTABLE_FIELD_NAMES = (
    "revenue",
    "arr",
    "mrr",
    "gross_margin",
    "ebitda",
    "burn_rate",
    "cash",
    "customers",
    "growth_rate",
    "cac",
    "ltv",
    "valuation",
)


class FinancialAnalysisServiceError(Exception):
    """Base exception for financial analysis orchestration failures."""


class BusinessAnalysisRequiredError(FinancialAnalysisServiceError):
    """Raised when financial analysis is requested before the
    document's business analysis (`DocumentAnalysis`) has been run.

    Financial extraction reads the existing business analysis as
    context, so it cannot run until that analysis exists.
    """


class FinancialMetricsNotFoundError(FinancialAnalysisServiceError):
    """Raised when a document has not yet had financial analysis run."""


def _normalize_and_compute(
    result: FinancialExtractionResult,
) -> FinancialMetricsCreate:
    """Normalize raw AI extraction into a persistable, KPI-complete record.

    Fills in derivable values the AI did not provide directly
    (`arr`/`mrr` cross-derivation, `runway_months`), and computes a
    `confidence_score` reflecting how much of the extractable data the
    AI actually found. All derivation happens here, in the service
    layer, rather than by asking the AI to compute or estimate figures.

    Args:
        result: The validated raw financial extraction result.

    Returns:
        A `FinancialMetricsCreate` ready to persist.
    """
    arr = result.arr
    mrr = result.mrr
    if arr is None and mrr is not None:
        arr = mrr * 12
    elif mrr is None and arr is not None:
        mrr = arr / 12

    runway_months = None
    if result.cash is not None and result.burn_rate is not None and result.burn_rate > 0:
        runway_months = round(result.cash / result.burn_rate, 1)

    populated_count = sum(
        1
        for field_name in _EXTRACTABLE_FIELD_NAMES
        if getattr(result, field_name) is not None
    )
    confidence_score = round(populated_count / len(_EXTRACTABLE_FIELD_NAMES), 2)

    return FinancialMetricsCreate(
        currency=result.currency,
        revenue=result.revenue,
        arr=arr,
        mrr=mrr,
        gross_margin=result.gross_margin,
        ebitda=result.ebitda,
        burn_rate=result.burn_rate,
        runway_months=runway_months,
        cash=result.cash,
        customers=result.customers,
        growth_rate=result.growth_rate,
        cac=result.cac,
        ltv=result.ltv,
        valuation=result.valuation,
        confidence_score=confidence_score,
    )


def _build_extraction_input(text_content: str, analysis_summary: str | None) -> str:
    """Combine the document's business analysis summary and raw text.

    Providing the existing business-analysis summary as context helps
    the model correctly attribute figures (e.g. distinguishing company
    revenue from a mentioned competitor's revenue) without re-deriving
    facts already established by the business analysis.

    Args:
        text_content: The document's extracted plain text.
        analysis_summary: The document's business-analysis summary, or
            `None` if it has none.

    Returns:
        The combined text to send for financial extraction.
    """
    if not analysis_summary:
        return text_content

    return (
        f"Business context summary: {analysis_summary}\n\n"
        f"Full document text:\n{text_content}"
    )


class FinancialAnalysisService:
    """Use cases for triggering and retrieving document financial analysis."""

    @staticmethod
    async def analyze_financial_metrics(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> FinancialMetrics:
        """Extract and persist financial KPIs for a document.

        Requires that the document's business analysis
        (`DocumentAnalysis`) already exists, since it is read as context
        for the financial extraction. If the document already has a
        financial metrics record, it is overwritten in place, since each
        document has at most one.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the user requesting analysis.

        Returns:
            The newly created or updated `FinancialMetrics` record.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization.
            BusinessAnalysisRequiredError: If the document has not yet
                had its business analysis (`DocumentAnalysis`) run.
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured, or it is rejected as invalid (propagated
                from `AIService`).
            AIRequestFailedError: If the OpenAI request fails after
                retrying once (propagated from `AIService`).
            InvalidAIResponseError: If the AI's response is not valid
                JSON or does not match the expected schema (propagated
                from `AIService`).
        """
        document = await DocumentService.get_document(db, document_id, actor_id)

        try:
            analysis = await DocumentAnalysisService.get_analysis(
                db, document_id, actor_id
            )
        except AnalysisNotFoundError as exc:
            raise BusinessAnalysisRequiredError(
                "This document must be analyzed (POST /documents/{id}/analyze) "
                "before financial metrics can be extracted."
            ) from exc

        extraction_input = _build_extraction_input(
            document.text_content or "", analysis.summary
        )
        raw_result = await AIService.extract_financial_metrics(extraction_input)
        metrics_data = _normalize_and_compute(raw_result)

        existing = await _get_existing_metrics(db, document_id)

        if existing is not None:
            _apply_metrics_data(existing, metrics_data)
            metrics = existing
        else:
            metrics = FinancialMetrics(
                document_id=document_id, **metrics_data.model_dump()
            )
            db.add(metrics)

        await db.commit()
        await db.refresh(metrics)
        return metrics

    @staticmethod
    async def get_financial_metrics(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> FinancialMetrics:
        """Fetch a document's existing financial metrics.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.

        Returns:
            The document's `FinancialMetrics` record.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization.
            FinancialMetricsNotFoundError: If the document has not yet
                had financial analysis run.
        """
        await DocumentService.get_document(db, document_id, actor_id)

        metrics = await _get_existing_metrics(db, document_id)
        if metrics is None:
            raise FinancialMetricsNotFoundError(
                "This document has not had financial analysis run yet."
            )

        return metrics


async def _get_existing_metrics(
    db: AsyncSession, document_id: uuid.UUID
) -> FinancialMetrics | None:
    """Fetch a document's financial metrics row, if one exists.

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


def _apply_metrics_data(
    metrics: FinancialMetrics, data: FinancialMetricsCreate
) -> None:
    """Overwrite an existing metrics row's fields with new data.

    Args:
        metrics: The existing `FinancialMetrics` to update in place.
        data: The new metrics data to apply.
    """
    for field, value in data.model_dump().items():
        setattr(metrics, field, value)