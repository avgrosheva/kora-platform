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
from app.models.qualitative_fact import QualitativeFactType
from app.schemas.document_analysis import DocumentAnalysisCreate
from app.services.ai_service import AIAnalysisResult, AIService
from app.services.document_service import DocumentNotFoundError, DocumentService

from app.services.ai_service import AIService, EXTRACTION_VERSION
from app.services.citation_service import CitationService
from app.services.qualitative_facts_service import QualitativeFactsService


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

    @staticmethod
    async def analyze_document_with_citations(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DocumentAnalysis:
        """Analyze a document and persist per-field source citations.

        Produces the same `DocumentAnalysis` row shape as
        `analyze_document` (full backward compatibility for existing
        API consumers), but additionally writes one `SourceCitation`
        row per non-null extracted field, including one per array item
        (each competitor, each risk gets its own citation). Also
        persists the extraction's structured `qualitative_facts` as
        `QualitativeFact` rows (Evidence Layer plan, Step 4), each with
        its own citation — this is additive to, not a replacement for,
        `main_risks`/`growth_opportunities`, which continue to populate
        `DocumentAnalysis.risks`/`opportunities` exactly as before.

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
                has not completed successfully.
            AIServiceNotConfiguredError, AIRequestFailedError,
            InvalidAIResponseError: Propagated from `AIService`.
        """
        document = await DocumentService.get_document(db, document_id, actor_id)

        if document.status != DocumentStatus.COMPLETED:
            raise DocumentNotProcessedError(
                "Document must be fully processed (status=completed) "
                "before it can be analyzed."
            )

        cited = await AIService.generate_cited_business_analysis(document.text_content or "")

        analysis_data = DocumentAnalysisCreate(
            summary=cited.summary.value,
            company_name=cited.company_name.value,
            industry=cited.industry.value,
            business_model=cited.business_model.value,
            key_products=[c.value for c in cited.key_products if c.value] or None,
            risks=[c.value for c in cited.main_risks if c.value] or None,
            opportunities=[c.value for c in cited.growth_opportunities if c.value] or None,
            revenue_streams=[c.value for c in cited.revenue_streams if c.value] or None,
            customers=[c.value for c in cited.target_customers if c.value] or None,
            competitors=[c.value for c in cited.competitors if c.value] or None,
            raw_json=cited.model_dump(),
        )

        existing = await _get_existing_analysis(db, document_id)
        if existing is not None:
            _apply_analysis_data(existing, analysis_data)
            analysis = existing
        else:
            analysis = DocumentAnalysis(document_id=document_id, **analysis_data.model_dump())
            db.add(analysis)

        await db.commit()
        await db.refresh(analysis)

        await _persist_citations_for_analysis(db, document_id, cited)
        await _persist_qualitative_facts(db, document_id, cited)

        return analysis


async def _persist_citations_for_analysis(db, document_id, cited) -> None:
    """Write one `SourceCitation` per non-null field in a cited analysis.

    Array fields get one citation per item, indexed in `field_path`
    (e.g. `"analysis.competitors[0]"`), so each competitor/risk/etc.
    is independently traceable.

    Args:
        db: The active database session.
        document_id: The document these citations belong to.
        cited: The validated `CitedBusinessAnalysisResult`.
    """
    scalar_fields = ["company_name", "industry", "business_model", "summary"]
    array_fields = [
        "key_products", "revenue_streams", "target_customers",
        "competitors", "main_risks", "growth_opportunities",
    ]

    for field_name in scalar_fields:
        cited_value = getattr(cited, field_name)
        if cited_value.value is not None and cited_value.quote:
            await CitationService.create_citation(
                db, document_id, f"analysis.{field_name}", cited_value.quote,
                page_number=cited_value.page_number, confidence=cited_value.confidence,
                extraction_version=EXTRACTION_VERSION,
            )

    for field_name in array_fields:
        for index, item in enumerate(getattr(cited, field_name)):
            if item.value is not None and item.quote:
                await CitationService.create_citation(
                    db, document_id, f"analysis.{field_name}[{index}]", item.quote,
                    page_number=item.page_number, confidence=item.confidence,
                    extraction_version=EXTRACTION_VERSION,
                )


async def _persist_qualitative_facts(db, document_id, cited) -> None:
    """Replace a document's structured qualitative facts with a fresh set.

    One `SourceCitation` is written per fact first (each qualitative
    fact always has a quote, unlike the flat financial pipeline, so
    every `QualitativeFact` this writes has a `source_citation_id` —
    contrast with `financial_analysis_service.py`'s flat-metric facts,
    which never do).

    Args:
        db: The active database session.
        document_id: The document these facts belong to.
        cited: The validated `CitedBusinessAnalysisResult`.
    """
    fact_dicts = []
    for index, item in enumerate(cited.qualitative_facts):
        citation = await CitationService.create_citation(
            db, document_id, f"qualitative_facts[{index}]", item.quote,
            page_number=item.page_number, confidence=item.confidence,
            extraction_version=EXTRACTION_VERSION,
        )
        fact_dicts.append({
            "category": item.category,
            "claim_text": item.claim_text,
            "fact_type": QualitativeFactType.DOCUMENT_STATED,
            "severity_hint": item.severity_hint,
            "confidence": item.confidence,
            "source_citation_id": citation.id,
        })

    await QualitativeFactsService.replace_facts(db, document_id, fact_dicts)


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