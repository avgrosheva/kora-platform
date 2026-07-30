"""AI due diligence copilot: full investment reports from existing data.

Aggregates all already-computed structured information about a document
(business analysis, financial metrics, investment score) together with
additional retrieved context via `RetrievalService`, and generates a
complete, section-by-section investment report via `AIService`. No new
AI pipeline is introduced — report generation reuses the same
structured-completion machinery already used for business and financial
analysis. No report is persisted; this is a synchronous, generate-on-
demand operation. Services operate directly on `AsyncSession` — there
is no repository layer in this project's architecture.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.document_analysis import DocumentAnalysis
from app.schemas.chat import ChatSource
from app.schemas.due_diligence import DueDiligenceResponse, DueDiligenceSection
from app.schemas.rag import SearchResultRead
from app.services.ai_service import AIService, DueDiligenceReportResult
from app.services.document_service import DocumentService
from app.services.financial_analysis_service import (
    FinancialAnalysisService,
    FinancialMetricsNotFoundError,
)
from app.services.investment_scoring_service import (
    InvestmentScoreNotFoundError,
    InvestmentScoringService,
)
from app.services.retrieval_service import RetrievalService

RETRIEVAL_QUERY_SUFFIX = (
    "business model, market, competition, financial performance, "
    "growth, traction, and risks"
)

SECTION_TITLES: tuple[tuple[str, str], ...] = (
    ("executive_summary", "Executive Summary"),
    ("company_overview", "Company Overview"),
    ("problem", "Problem"),
    ("solution", "Solution"),
    ("business_model", "Business Model"),
    ("market", "Market"),
    ("competition", "Competition"),
    ("traction", "Traction"),
    ("financial_analysis", "Financial Analysis"),
    ("growth", "Growth"),
    ("risks", "Risks"),
    ("red_flags", "Red Flags"),
    ("investment_thesis", "Investment Thesis"),
    ("recommendation", "Recommendation"),
    ("confidence_level", "Confidence Level"),
    ("open_questions", "Open Questions"),
)
"""The fixed order and display titles of report sections, matching the
field names on `DueDiligenceReportResult` exactly."""

_MISSING = "Not available."


class DueDiligenceServiceError(Exception):
    """Base exception for due diligence report generation failures."""


class DocumentNotProcessedError(DueDiligenceServiceError):
    """Raised when a report is requested for a document whose text
    extraction has not completed successfully.

    Text extraction must have completed, since both the retrieval query
    and any structured data available depend on the document having
    been processed at all.
    """


@dataclass(frozen=True)
class DueDiligenceContext:
    """Plain, DB-independent snapshot of a document's available structured data.

    Deliberately holds no ORM references, so `build_due_diligence_prompt`
    can be unit-tested with plain literals and no database access.

    Attributes:
        original_filename: The document's original filename, used as a
            fallback identifier when no company name is known.
        company_name: The company's name, or `None` if not identified.
        industry: The company's industry, or `None`.
        business_model: The company's business model, or `None`.
        analysis_summary: The business analysis's summary, or `None`.
        key_products: The company's key products, or `None`.
        revenue_streams: The company's revenue streams, or `None`.
        target_customers: The company's target customers, or `None`.
        competitors: The company's competitors, or `None`.
        main_risks: The company's main risks (from business analysis),
            or `None`.
        growth_opportunities: Growth opportunities (from business
            analysis), or `None`.
        currency: The ISO 4217 currency code for monetary fields, or
            `None`.
        revenue: Total revenue, or `None`.
        arr: Annual recurring revenue, or `None`.
        mrr: Monthly recurring revenue, or `None`.
        gross_margin: Gross margin (%), or `None`.
        ebitda: EBITDA, or `None`.
        burn_rate: Monthly cash burn rate, or `None`.
        runway_months: Months of runway remaining, or `None`.
        cash: Cash on hand, or `None`.
        customer_count: Number of customers, or `None`.
        growth_rate: Growth rate (%), or `None`.
        valuation: Company valuation, or `None`.
        overall_score: Overall investment score (0-100), or `None`.
        financial_score: Financial sub-score, or `None`.
        growth_score: Growth sub-score, or `None`.
        risk_score: Risk (stability) sub-score, or `None`.
        market_score: Market sub-score, or `None`.
        score_confidence: The investment score's confidence (0.0-1.0),
            or `None`.
        scoring_reasoning: The deterministic scoring engine's
            human-readable reasoning, or `None`.
    """

    original_filename: str
    company_name: str | None = None
    industry: str | None = None
    business_model: str | None = None
    analysis_summary: str | None = None
    key_products: list[str] | None = None
    revenue_streams: list[str] | None = None
    target_customers: list[str] | None = None
    competitors: list[str] | None = None
    main_risks: list[str] | None = None
    growth_opportunities: list[str] | None = None
    currency: str | None = None
    revenue: float | None = None
    arr: float | None = None
    mrr: float | None = None
    gross_margin: float | None = None
    ebitda: float | None = None
    burn_rate: float | None = None
    runway_months: float | None = None
    cash: float | None = None
    customer_count: int | None = None
    growth_rate: float | None = None
    valuation: float | None = None
    overall_score: float | None = None
    financial_score: float | None = None
    growth_score: float | None = None
    risk_score: float | None = None
    market_score: float | None = None
    score_confidence: float | None = None
    scoring_reasoning: str | None = None


def _format_list(items: list[str] | None) -> str:
    """Format an optional list of strings for prompt inclusion.

    Args:
        items: The list to format, or `None`.

    Returns:
        A comma-separated string, or the standard "not available"
        marker if `items` is `None` or empty.
    """
    if not items:
        return _MISSING
    return ", ".join(items)


def _format_number(value: float | int | None, suffix: str = "") -> str:
    """Format an optional numeric value for prompt inclusion.

    Args:
        value: The value to format, or `None`.
        suffix: An optional unit suffix (e.g. `"%"`).

    Returns:
        The formatted value with suffix, or the standard "not
        available" marker if `value` is `None`.
    """
    if value is None:
        return _MISSING
    return f"{value:,.2f}{suffix}"


def build_due_diligence_prompt(
    context: DueDiligenceContext, chunks: list[SearchResultRead]
) -> str:
    """Build the user message for due diligence report generation.

    This is a pure function of its inputs — the same `context` and
    `chunks` (in the same order) always produce byte-identical output.
    The system prompt (fixed reporting rules and JSON schema) lives in
    `AIService._DUE_DILIGENCE_SYSTEM_PROMPT` and does not depend on any
    per-document data, so only the user message needs to be built here.

    Args:
        context: The document's available structured data.
        chunks: Additional retrieved document excerpts to use as
            supporting evidence, in the order they should be presented
            (highest similarity first). May be empty if nothing was
            retrieved.

    Returns:
        The assembled user message.
    """
    company_label = context.company_name or context.original_filename

    structured_data = "\n".join(
        [
            f"Company: {company_label}",
            f"Industry: {context.industry or _MISSING}",
            f"Business model (from analysis): {context.business_model or _MISSING}",
            f"Analysis summary: {context.analysis_summary or _MISSING}",
            f"Key products: {_format_list(context.key_products)}",
            f"Revenue streams: {_format_list(context.revenue_streams)}",
            f"Target customers: {_format_list(context.target_customers)}",
            f"Competitors: {_format_list(context.competitors)}",
            f"Main risks (from analysis): {_format_list(context.main_risks)}",
            f"Growth opportunities (from analysis): "
            f"{_format_list(context.growth_opportunities)}",
            "",
            f"Currency: {context.currency or _MISSING}",
            f"Revenue: {_format_number(context.revenue)}",
            f"ARR: {_format_number(context.arr)}",
            f"MRR: {_format_number(context.mrr)}",
            f"Gross margin: {_format_number(context.gross_margin, '%')}",
            f"EBITDA: {_format_number(context.ebitda)}",
            f"Monthly burn rate: {_format_number(context.burn_rate)}",
            f"Runway (months): {_format_number(context.runway_months)}",
            f"Cash on hand: {_format_number(context.cash)}",
            f"Customer count: {_format_number(context.customer_count)}",
            f"Growth rate: {_format_number(context.growth_rate, '%')}",
            f"Valuation: {_format_number(context.valuation)}",
            "",
            f"Overall investment score: {_format_number(context.overall_score)}/100",
            f"Financial sub-score: {_format_number(context.financial_score)}/100",
            f"Growth sub-score: {_format_number(context.growth_score)}/100",
            f"Risk (stability) sub-score: {_format_number(context.risk_score)}/100",
            f"Market sub-score: {_format_number(context.market_score)}/100",
            f"Score confidence: {_format_number(context.score_confidence)}",
            f"Scoring reasoning: {context.scoring_reasoning or _MISSING}",
        ]
    )

    if chunks:
        excerpts = "\n\n".join(
            f"[Excerpt {index + 1}] (document {chunk.document_id}, "
            f"chunk {chunk.chunk_index}):\n{chunk.text}"
            for index, chunk in enumerate(chunks)
        )
    else:
        excerpts = (
            "No additional document excerpts were retrieved. Base the "
            "report only on the structured data above, and state "
            "explicitly wherever information is not available."
        )

    return (
        f"Structured data:\n{structured_data}\n\n"
        f"Document excerpts:\n{excerpts}\n\n"
        f"Generate the complete due diligence report as instructed."
    )


async def _fetch_analysis_dict(
    db: AsyncSession, document_id: uuid.UUID
) -> DocumentAnalysis | None:
    """Fetch a document's business analysis via a direct, read-only query.

    Reads directly rather than through `DocumentAnalysisService` (which
    is not in this feature's required reuse list), consistent with how
    `portfolio_service.py` and `dashboard_service.py` already read
    `DocumentAnalysis` directly for aggregation purposes.

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


def _build_context(
    document: Document, analysis: DocumentAnalysis | None, financial_metrics, score
) -> DueDiligenceContext:
    """Assemble a `DueDiligenceContext` from the fetched ORM objects.

    Args:
        document: The document being reported on.
        analysis: The document's business analysis, or `None`.
        financial_metrics: The document's financial metrics, or `None`.
        score: The document's investment score, or `None`.

    Returns:
        The assembled, DB-independent context.
    """
    return DueDiligenceContext(
        original_filename=document.original_filename,
        company_name=analysis.company_name if analysis else None,
        industry=analysis.industry if analysis else None,
        business_model=analysis.business_model if analysis else None,
        analysis_summary=analysis.summary if analysis else None,
        key_products=analysis.key_products if analysis else None,
        revenue_streams=analysis.revenue_streams if analysis else None,
        target_customers=analysis.customers if analysis else None,
        competitors=analysis.competitors if analysis else None,
        main_risks=analysis.risks if analysis else None,
        growth_opportunities=analysis.opportunities if analysis else None,
        currency=financial_metrics.currency if financial_metrics else None,
        revenue=financial_metrics.revenue if financial_metrics else None,
        arr=financial_metrics.arr if financial_metrics else None,
        mrr=financial_metrics.mrr if financial_metrics else None,
        gross_margin=financial_metrics.gross_margin if financial_metrics else None,
        ebitda=financial_metrics.ebitda if financial_metrics else None,
        burn_rate=financial_metrics.burn_rate if financial_metrics else None,
        runway_months=(
            financial_metrics.runway_months if financial_metrics else None
        ),
        cash=financial_metrics.cash if financial_metrics else None,
        customer_count=financial_metrics.customers if financial_metrics else None,
        growth_rate=financial_metrics.growth_rate if financial_metrics else None,
        valuation=financial_metrics.valuation if financial_metrics else None,
        overall_score=score.overall_score if score else None,
        financial_score=score.financial_score if score else None,
        growth_score=score.growth_score if score else None,
        risk_score=score.risk_score if score else None,
        market_score=score.market_score if score else None,
        score_confidence=score.confidence_score if score else None,
        scoring_reasoning=score.reasoning if score else None,
    )


def _report_to_sections(report: DueDiligenceReportResult) -> list[DueDiligenceSection]:
    """Convert a validated AI report into ordered, titled sections.

    Args:
        report: The validated due diligence report.

    Returns:
        The report's sections, in the fixed order defined by
        `SECTION_TITLES`.
    """
    report_data = report.model_dump()
    return [
        DueDiligenceSection(title=title, content=report_data[field_name])
        for field_name, title in SECTION_TITLES
    ]


class DueDiligenceService:
    """Generates complete, evidence-grounded investment reports."""

    @staticmethod
    async def generate_report(
        db: AsyncSession,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
        top_k: int,
    ) -> DueDiligenceResponse:
        """Generate a complete due diligence report for a document.

        Collects all already-computed structured information (business
        analysis, financial metrics, investment score), retrieves
        additional supporting context via `RetrievalService`, and
        generates the report via a single call to `AIService`. Exactly
        one embedding call (inside `RetrievalService.semantic_search`)
        and one chat-completion call (inside
        `AIService.generate_due_diligence_report`) are made — no
        duplicate AI calls occur, and no existing analysis, financial
        extraction, or scoring is re-run.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.
            top_k: The maximum number of document excerpts to retrieve
                as additional context.

        Returns:
            The complete due diligence report.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization
                (propagated from `DocumentService.get_document`).
            DocumentNotProcessedError: If the document's text
                extraction has not completed successfully.
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured, or it is rejected as invalid (propagated
                from `AIService` or, via retrieval, `EmbeddingService`).
            AIRequestFailedError: If the report-generation request fails
                after retrying once (propagated from `AIService`).
            InvalidAIResponseError: If the AI's response is not valid
                JSON or does not match the expected schema (propagated
                from `AIService`).
            EmbeddingServiceNotConfiguredError: If no OpenAI API key is
                configured for embeddings (propagated from
                `RetrievalService`).
            EmbeddingRequestFailedError: If the retrieval query's
                embedding request fails after retrying once (propagated
                from `RetrievalService`).
            InvalidEmbeddingDimensionError: If the retrieval query's
                embedding has the wrong dimensionality (propagated from
                `RetrievalService`).
        """
        document = await DocumentService.get_document(db, document_id, actor_id)

        if document.status != DocumentStatus.COMPLETED:
            raise DocumentNotProcessedError(
                "Document must be fully processed (status=completed) "
                "before a due diligence report can be generated."
            )

        analysis = await _fetch_analysis_dict(db, document_id)

        try:
            financial_metrics = await FinancialAnalysisService.get_financial_metrics(
                db, document_id, actor_id
            )
        except FinancialMetricsNotFoundError:
            financial_metrics = None

        try:
            score = await InvestmentScoringService.get_score(
                db, document_id, actor_id
            )
        except InvestmentScoreNotFoundError:
            score = None

        retrieval_query = " ".join(
            filter(None, [analysis.company_name if analysis else None, RETRIEVAL_QUERY_SUFFIX])
        )
        chunks = await RetrievalService.semantic_search(
            db=db,
            organization_id=document.organization_id,
            actor_id=actor_id,
            query=retrieval_query,
            top_k=top_k,
        )

        context = _build_context(document, analysis, financial_metrics, score)
        user_message = build_due_diligence_prompt(context, chunks)

        report = await AIService.generate_due_diligence_report(user_message)

        sources = [
            ChatSource(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                similarity_score=chunk.similarity_score,
                snippet=chunk.text[:300],
            )
            for chunk in chunks
        ]

        return DueDiligenceResponse(
            document_id=document_id,
            sections=_report_to_sections(report),
            sources=sources,
            model_used=_current_model_name(),
        )


def _current_model_name() -> str:
    """Return the currently configured chat/completion model name.

    Kept as a tiny indirection so the response always reflects the
    model actually used, sourced from the same `Settings` the rest of
    `AIService` reads from.

    Returns:
        The configured OpenAI model identifier.
    """
    from app.config import get_settings

    return get_settings().OPENROUTER_CHAT_MODEL