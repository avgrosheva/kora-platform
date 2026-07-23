"""Document AI-analysis orchestration.

Loads a processed document, sends its extracted text to `AIService`, and
persists the resulting structured analysis. Services operate directly
on `AsyncSession` — there is no repository layer in this project's
architecture.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.document_analysis import DocumentAnalysis
from app.schemas.document_analysis import DocumentAnalysisCreate
from app.services.ai_service import AIAnalysisResult, AIService
from app.services.document_service import DocumentNotFoundError, DocumentService


class DocumentAnalysisServiceError(Exception):
    """Base exception for document analysis orchestration failures."""


class DocumentNotProcessedError(DocumentAnalysisServiceError):
    """Raised when analysis is requested for a document whose text
    extraction has not completed successfully."""


class AnalysisNotFoundError(DocumentAnalysisServiceError):
    """Raised when a document has not yet been analyzed."""


def _to_analysis_create(result: AIAnalysisResult) -> DocumentAnalysisCreate:
    """Map the AI's output schema onto the database's field names.

    The AI's schema uses `target_customers`, `main_risks`, and
    `growth_opportunities` (matching the prompt's requested wording).
    The database uses the shorter names `customers`, `risks`, and
    `opportunities` (per the required model fields). This function is
    the single place that translation happens.

    Args:
        result: The validated AI analysis result.

    Returns:
        A `DocumentAnalysisCreate` ready to persist.
    """
    return DocumentAnalysisCreate(
        summary=result.summary,
        company_name=result.company_name,
        industry=result.industry,
        business_model=result.business_model,
        key_products=result.key_products,
        risks=result.main_risks,
        opportunities=result.growth_opportunities,
        revenue_streams=result.revenue_streams,
        customers=result.target_customers,
        competitors=result.competitors,
        raw_json=result.model_dump(),
    )


class DocumentAnalysisService:
    """Use cases for triggering and retrieving document AI analysis."""

    @staticmethod
    async def analyze_document(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DocumentAnalysis:
        """Analyze a processed document's text and persist the result.

        If the document already has an analysis, it is overwritten in
        place, since each document has at most one analysis.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the user requesting analysis.

        Returns:
            The newly created or updated `DocumentAnalysis`.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization.
            DocumentNotProcessedError: If the document's text extraction
                has not completed successfully (`status != COMPLETED`).
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

        if document.status != DocumentStatus.COMPLETED:
            raise DocumentNotProcessedError(
                "Document must be fully processed (status=completed) "
                "before it can be analyzed."
            )

        ai_result = await AIService.analyze_document_text(document.text_content or "")
        analysis_data = _to_analysis_create(ai_result)

        existing = await _get_existing_analysis(db, document_id)

        if existing is not None:
            _apply_analysis_data(existing, analysis_data)
            analysis = existing
        else:
            analysis = DocumentAnalysis(
                document_id=document_id, **analysis_data.model_dump()
            )
            db.add(analysis)

        await db.commit()
        await db.refresh(analysis)
        return analysis

    @staticmethod
    async def get_analysis(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DocumentAnalysis:
        """Fetch a document's existing analysis.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.

        Returns:
            The document's `DocumentAnalysis`.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization.
            AnalysisNotFoundError: If the document has not yet been
                analyzed.
        """
        await DocumentService.get_document(db, document_id, actor_id)

        analysis = await _get_existing_analysis(db, document_id)
        if analysis is None:
            raise AnalysisNotFoundError(
                "This document has not been analyzed yet."
            )

        return analysis


async def _get_existing_analysis(
    db: AsyncSession, document_id: uuid.UUID
) -> DocumentAnalysis | None:
    """Fetch a document's analysis row, if one exists.

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


def _apply_analysis_data(
    analysis: DocumentAnalysis, data: DocumentAnalysisCreate
) -> None:
    """Overwrite an existing analysis row's fields with new data.

    Args:
        analysis: The existing `DocumentAnalysis` to update in place.
        data: The new analysis data to apply.
    """
    for field, value in data.model_dump().items():
        setattr(analysis, field, value)