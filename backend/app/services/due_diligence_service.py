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
from app.services.evidence_service import EvidenceFact, EvidenceService
from app.services.financial_analysis_service import (
    FinancialAnalysisService,
    FinancialMetricsNotFoundError,
)
from app.services.findings_service import Finding, FindingsService, FindingSeverity, FindingType
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
        evidence: The document's unified evidence (`EvidenceService`),
            covering `financial_facts` (with periods, unlike the flat
            snapshot above), `DocumentAnalysis` fields, and qualitative
            facts. Bug C fix (Evidence Layer plan, Step 6): the report's
            narrative previously never saw this, only the flat scalar
            fields above.
        findings: The document's unified findings (`FindingsService`) —
            deterministic checks, document-stated risk claims, and
            Kora's own inferences. Explicitly included in the prompt,
            grouped by severity, so the model's own narrative can no
            longer contradict what Kora already knows (Bug C).
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
    evidence: list[EvidenceFact] | None = None
    findings: list[Finding] | None = None


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


_EVIDENCE_CATEGORY_DISPLAY: dict[str, str] = {
    "financial": "Financial",
    "company": "Company",
    "market": "Market",
    "team": "Team",
}


def _format_evidence(evidence: list[EvidenceFact] | None) -> str:
    """Format a document's unified evidence for prompt inclusion, by category.

    Args:
        evidence: The document's evidence, as returned by
            `EvidenceService.get_evidence`, or `None`.

    Returns:
        A category-grouped listing of every fact's field name, value,
        and period (where applicable), or the standard "not available"
        marker if there is none.
    """
    if not evidence:
        return _MISSING

    lines: list[str] = []
    for category, label in _EVIDENCE_CATEGORY_DISPLAY.items():
        facts_in_category = [fact for fact in evidence if fact.category == category]
        if not facts_in_category:
            continue
        lines.append(f"{label}:")
        for fact in facts_in_category:
            period_suffix = f" ({fact.period})" if fact.period else ""
            lines.append(f"  - {fact.field_name}{period_suffix}: {fact.display_value}")
    return "\n".join(lines) if lines else _MISSING


_FINDING_TYPE_LABEL: dict[FindingType, str] = {
    FindingType.DETERMINISTIC: "Deterministic check",
    FindingType.DOCUMENT_STATED: "Document-stated",
    FindingType.DERIVED: "Derived",
    FindingType.AI_INFERRED: "Kora-inferred",
}

_FINDING_SEVERITY_DISPLAY_ORDER: tuple[FindingSeverity, ...] = (
    FindingSeverity.CRITICAL,
    FindingSeverity.HIGH,
    FindingSeverity.MEDIUM,
    FindingSeverity.LOW,
    FindingSeverity.INFORMATIONAL,
)


def _format_findings(findings: list[Finding] | None) -> str:
    """Format a document's unified findings for prompt inclusion, by severity.

    This is the core of the Bug C fix: the model sees every deterministic
    check, document-stated risk, and Kora-inferred concern *before*
    writing the report's own Risks/Red Flags narrative, so its narrative
    has no way to contradict what Kora already knows. Every entry's
    `[type]` label (e.g. `[Kora-inferred]`) is passed straight through
    into the prompt, so the model is never in a position to blur a
    Kora-inferred conclusion into a document-stated fact.

    Args:
        findings: The document's findings, as returned by
            `FindingsService.get_findings`, or `None`.

    Returns:
        A severity-grouped listing, or the standard "not available"
        marker if there are none.
    """
    if not findings:
        return _MISSING

    lines: list[str] = []
    for severity in _FINDING_SEVERITY_DISPLAY_ORDER:
        group = [finding for finding in findings if finding.severity == severity]
        if not group:
            continue
        lines.append(f"{severity.value.upper()} severity:")
        for finding in group:
            type_label = _FINDING_TYPE_LABEL.get(finding.type, finding.type.value)
            detail = finding.explanation or finding.evidence or ""
            lines.append(f"  - [{type_label}] {finding.title}: {detail}")
    return "\n".join(lines) if lines else _MISSING


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
            "",
            "Extracted evidence (Kora's unified evidence layer):",
            _format_evidence(context.evidence),
            "",
            "Findings (Kora's deterministic checks, document-stated risk "
            "claims, and Kora's own inferences — grouped by severity; "
            "every one of these MUST be reflected in the Risks and Red "
            "Flags sections, not omitted):",
            _format_findings(context.findings),
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
    document: Document,
    analysis: DocumentAnalysis | None,
    financial_metrics,
    score,
    evidence: list[EvidenceFact],
    findings: list[Finding],
) -> DueDiligenceContext:
    """Assemble a `DueDiligenceContext` from the fetched ORM objects.

    Args:
        document: The document being reported on.
        analysis: The document's business analysis, or `None`.
        financial_metrics: The document's financial metrics, or `None`.
        score: The document's investment score, or `None`.
        evidence: The document's unified evidence (`EvidenceService`).
        findings: The document's unified findings (`FindingsService`).

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
        evidence=evidence,
        findings=findings,
    )


_SURFACED_SEVERITIES: tuple[FindingSeverity, ...] = (FindingSeverity.CRITICAL, FindingSeverity.HIGH)


def _finding_is_mentioned(finding: Finding, report_text: str) -> bool:
    """Check whether a finding's title appears anywhere in the report's text.

    A simple case-insensitive substring check on `title` (a short,
    stable, human-readable label) rather than anything more elaborate —
    this only needs to catch the case where the model discussed a
    finding somewhere in its own words versus omitted it entirely, not
    to grade the quality of the discussion.

    Args:
        finding: The finding to look for.
        report_text: The combined text of every report section.

    Returns:
        `True` if the finding's title is present (case-insensitively).
    """
    return finding.title.lower() in report_text.lower()


def ensure_critical_findings_are_surfaced(
    sections: list[DueDiligenceSection], findings: list[Finding]
) -> list[DueDiligenceSection]:
    """Guarantee every CRITICAL/HIGH finding is reflected in the report.

    This is the Bug C fix's second half: `build_due_diligence_prompt`
    already tells the model about every finding, but an instruction is
    not a guarantee — this is a deterministic, post-generation check
    that makes the "no red flags identified while red_flags is non-empty"
    contradiction structurally impossible, regardless of what the model
    actually wrote. Findings already mentioned somewhere in the report
    (in the model's own words) are left untouched; only genuinely
    omitted CRITICAL/HIGH findings are injected, appended verbatim to
    the Red Flags section rather than silently dropped.

    Args:
        sections: The report's sections, as generated.
        findings: The document's unified findings.

    Returns:
        The sections, unchanged if every CRITICAL/HIGH finding was
        already mentioned somewhere in the report (or there are none);
        otherwise a new list with the Red Flags section's content
        extended to include whichever were omitted.
    """
    must_be_surfaced = [finding for finding in findings if finding.severity in _SURFACED_SEVERITIES]
    if not must_be_surfaced:
        return sections

    combined_text = "\n".join(section.content for section in sections)
    omitted = [finding for finding in must_be_surfaced if not _finding_is_mentioned(finding, combined_text)]
    if not omitted:
        return sections

    addendum_lines = [
        f"- {finding.title} ({finding.severity.value}): {finding.explanation or finding.evidence or ''}"
        for finding in omitted
    ]
    addendum = (
        "\n\nThe following findings were identified by Kora's deterministic "
        "checks and evidence extraction and must be considered regardless of "
        "whether they are discussed above:\n" + "\n".join(addendum_lines)
    )

    return [
        DueDiligenceSection(title=section.title, content=section.content + addendum)
        if section.title == "Red Flags"
        else section
        for section in sections
    ]


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
        analysis, financial metrics, investment score, and — Bug C fix,
        Evidence Layer plan Step 6 — the unified evidence and findings
        from `EvidenceService`/`FindingsService`), retrieves additional
        supporting context via `RetrievalService`, and generates the
        report via a single call to `AIService`. Every finding is passed
        into the prompt grouped by severity before the model writes its
        own Risks/Red Flags narrative; after generation,
        `ensure_critical_findings_are_surfaced` deterministically checks
        that every CRITICAL/HIGH finding is actually mentioned somewhere
        in the report, injecting any the model silently omitted rather
        than allowing a "no red flags identified" narrative to coexist
        with non-empty structured findings. Exactly one embedding call
        (inside `RetrievalService.semantic_search`) and one chat-completion
        call (inside
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

        evidence = await EvidenceService.get_evidence(db, document_id)
        findings = await FindingsService.get_findings(db, document_id)

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

        context = _build_context(document, analysis, financial_metrics, score, evidence, findings)
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

        sections = ensure_critical_findings_are_surfaced(_report_to_sections(report), findings)

        return DueDiligenceResponse(
            document_id=document_id,
            sections=sections,
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