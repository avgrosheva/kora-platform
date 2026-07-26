"""Export of due diligence reports as Markdown and PDF.

Renders the report produced by `DueDiligenceService` into downloadable
file formats. No AI generation happens in this module — it consumes
`DueDiligenceService.generate_report` exactly once per export call and
performs pure formatting/layout on the result. No files, markdown, or
PDFs are persisted; everything is generated synchronously and returned
in-memory. Services operate directly on `AsyncSession` — there is no
repository layer in this project's architecture.
"""

import io
import uuid
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.schemas.due_diligence import DueDiligenceResponse
from app.services.document_service import DocumentService
from app.services.due_diligence_service import DueDiligenceService

DEFAULT_RETRIEVAL_TOP_K = 8

SUPPORTED_FORMATS = ("markdown", "pdf")


class ReportExportServiceError(Exception):
    """Base exception for report export failures."""


class ReportRenderingFailedError(ReportExportServiceError):
    """Raised when a successfully generated report could not be rendered
    into the requested export format (e.g. a PDF layout failure)."""


def _safe_filename_stub(name: str) -> str:
    """Sanitize a filename component to only safe characters.

    Args:
        name: The raw name to sanitize (e.g. a document's original
            filename).

    Returns:
        A filename-safe stub containing only alphanumerics, hyphens,
        and underscores.
    """
    cleaned = "".join(char if char.isalnum() or char in "-_" else "-" for char in name)
    cleaned = "-".join(filter(None, cleaned.split("-")))
    return cleaned or "document"


async def _fetch_organization_name(
    db: AsyncSession, organization_id: uuid.UUID
) -> str:
    """Fetch an organization's display name via a direct, read-only query.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        The organization's name, or a fallback string if somehow not
        found (should not occur in practice, since the caller has
        already been verified as a member of this organization).
    """
    result = await db.execute(
        select(Organization.name).where(Organization.id == organization_id)
    )
    name = result.scalar_one_or_none()
    return name or "Unknown Organization"


def render_markdown(
    report: DueDiligenceResponse,
    organization_name: str,
    document_name: str,
    generated_at: datetime,
) -> str:
    """Render a due diligence report as a clean Markdown document.

    Pure function of its inputs — no I/O, no AI calls. Every report
    section is included as its own heading, in the order provided.

    Args:
        report: The due diligence report to render.
        organization_name: The organization's display name.
        document_name: The source document's original filename.
        generated_at: The timestamp to display as the generation time.

    Returns:
        The complete Markdown document as a string.
    """
    lines = [
        f"# Due Diligence Report: {document_name}",
        "",
        f"**Organization:** {organization_name}  ",
        f"**Document:** {document_name}  ",
        f"**Generated:** {generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Model used:** {report.model_used}",
        "",
        "---",
        "",
    ]

    for section in report.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(section.content)
        lines.append("")

    if report.sources:
        lines.append("## Sources")
        lines.append("")
        for index, source in enumerate(report.sources, start=1):
            lines.append(
                f"{index}. Document `{source.document_id}`, chunk "
                f"{source.chunk_index} (similarity "
                f"{source.similarity_score:.3f}): {source.snippet}"
            )
        lines.append("")

    return "\n".join(lines)


class _NumberedCanvas(Canvas):
    """A ReportLab canvas that adds "Page X of Y" footers on save.

    Page counts aren't known until every page has been laid out, so
    page-number drawing is deferred: each page's state is captured on
    `showPage`, and the footer is drawn for every page only once the
    total page count is known, in `save`.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the canvas and its per-page state buffer."""
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []

    def showPage(self) -> None:
        """Capture the current page's state instead of finalizing it."""
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        """Draw page-number footers on every captured page, then save."""
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(total_pages)
            super().showPage()
        super().save()

    def _draw_page_number(self, total_pages: int) -> None:
        """Draw the "Page X of Y" footer for the current page.

        The title page (page 1) is intentionally left unnumbered, since
        it functions as a cover page rather than body content.

        Args:
            total_pages: The total number of pages in the document.
        """
        if self.getPageNumber() == 1:
            return
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.gray)
        self.drawRightString(
            LETTER[0] - 0.75 * inch,
            0.5 * inch,
            f"Page {self.getPageNumber()} of {total_pages}",
        )


class _ReportDocTemplate(BaseDocTemplate):
    """A `BaseDocTemplate` that registers section headings for the TOC.

    Each flowable styled as `SectionHeading` is bookmarked and added to
    the PDF's outline (sidebar navigation) and its table of contents,
    via ReportLab's standard `notify('TOCEntry', ...)` mechanism.
    """

    def afterFlowable(self, flowable) -> None:
        """Register section headings with the table of contents.

        Args:
            flowable: The flowable that was just rendered.
        """
        if isinstance(flowable, Paragraph) and flowable.style.name == "SectionHeading":
            text = flowable.getPlainText()
            self.canv.bookmarkPage(text)
            self.canv.addOutlineEntry(text, text, level=0, closed=False)
            self.notify("TOCEntry", (0, text, self.page))


def render_pdf(
    report: DueDiligenceResponse,
    organization_name: str,
    document_name: str,
    generated_at: datetime,
) -> bytes:
    """Render a due diligence report as a professional PDF.

    Produces a title page (organization, document name, generation
    timestamp, model used), a table of contents, and one section per
    heading, with page numbers on every page after the title page.

    Args:
        report: The due diligence report to render.
        organization_name: The organization's display name.
        document_name: The source document's original filename.
        generated_at: The timestamp to display as the generation time.

    Returns:
        The complete PDF document as raw bytes.

    Raises:
        ReportRenderingFailedError: If PDF layout/rendering fails for
            any reason.
    """
    try:
        return _build_pdf_bytes(report, organization_name, document_name, generated_at)
    except Exception as exc:  # noqa: BLE001 - any rendering failure must be reported, not silently swallowed
        raise ReportRenderingFailedError(f"Failed to render PDF: {exc}") from exc


def _build_pdf_bytes(
    report: DueDiligenceResponse,
    organization_name: str,
    document_name: str,
    generated_at: datetime,
) -> bytes:
    """Build the PDF document bytes using ReportLab's platypus API.

    Args:
        report: The due diligence report to render.
        organization_name: The organization's display name.
        document_name: The source document's original filename.
        generated_at: The timestamp to display as the generation time.

    Returns:
        The complete PDF document as raw bytes.
    """
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=24, spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=4,
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading1"], spaceBefore=18, spaceAfter=8
    )
    body_style = ParagraphStyle(
        "SectionBody", parent=styles["BodyText"], spaceAfter=10, leading=14
    )
    toc_heading_style = ParagraphStyle(
        "TOCHeading", parent=styles["Heading1"], spaceAfter=12
    )

    frame = Frame(
        0.75 * inch,
        0.75 * inch,
        LETTER[0] - 1.5 * inch,
        LETTER[1] - 1.5 * inch,
        id="normal",
    )
    doc = _ReportDocTemplate(
        buffer,
        pagesize=LETTER,
        title=f"Due Diligence Report - {document_name}",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

    story: list = []

    # --- Title page ---
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("Due Diligence Report", title_style))
    story.append(Paragraph(document_name, subtitle_style))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"Organization: {organization_name}", subtitle_style))
    story.append(
        Paragraph(
            f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle_style,
        )
    )
    story.append(Paragraph(f"Model used: {report.model_used}", subtitle_style))
    story.append(PageBreak())

    # --- Table of contents ---
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle(name="TOCLevel0", fontSize=11, leading=18)]
    story.append(Paragraph("Table of Contents", toc_heading_style))
    story.append(toc)
    story.append(PageBreak())

    # --- Report sections ---
    for section in report.sections:
        story.append(Paragraph(section.title, heading_style))
        for paragraph_text in section.content.split("\n"):
            if paragraph_text.strip():
                story.append(Paragraph(paragraph_text, body_style))
        story.append(Spacer(1, 6))

    # --- Sources ---
    if report.sources:
        story.append(Paragraph("Sources", heading_style))
        for index, source in enumerate(report.sources, start=1):
            citation = (
                f"{index}. Document {source.document_id}, chunk "
                f"{source.chunk_index} (similarity "
                f"{source.similarity_score:.3f}): {source.snippet}"
            )
            story.append(Paragraph(citation, body_style))

    doc.multiBuild(story, canvasmaker=_NumberedCanvas)
    return buffer.getvalue()


class ReportExportService:
    """Generates downloadable Markdown/PDF exports of due diligence reports."""

    @staticmethod
    async def export_markdown(
        db: AsyncSession,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
        top_k: int = DEFAULT_RETRIEVAL_TOP_K,
    ) -> tuple[str, str]:
        """Generate a due diligence report and render it as Markdown.

        Calls `DueDiligenceService.generate_report` exactly once — no
        separate AI pipeline, no duplicate generation.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.
            top_k: The number of retrieved excerpts to use as context,
                passed through to `DueDiligenceService`.

        Returns:
            A tuple of `(filename, markdown_content)`.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization
                (propagated from `DueDiligenceService`).
            DocumentNotProcessedError: If the document's text extraction
                has not completed successfully (propagated from
                `DueDiligenceService`).
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured (propagated from `DueDiligenceService`).
            AIRequestFailedError: If report generation fails after
                retrying once (propagated from `DueDiligenceService`).
            InvalidAIResponseError: If the AI's response is invalid
                (propagated from `DueDiligenceService`).
            EmbeddingServiceNotConfiguredError: If no OpenAI API key is
                configured for embeddings (propagated from
                `DueDiligenceService`).
            EmbeddingRequestFailedError: If the retrieval query's
                embedding request fails (propagated from
                `DueDiligenceService`).
            InvalidEmbeddingDimensionError: If the retrieval query's
                embedding has the wrong dimensionality (propagated from
                `DueDiligenceService`).
        """
        report = await DueDiligenceService.generate_report(
            db, document_id, actor_id, top_k
        )
        document = await DocumentService.get_document(db, document_id, actor_id)
        organization_name = await _fetch_organization_name(
            db, document.organization_id
        )
        generated_at = datetime.now(timezone.utc)

        content = render_markdown(
            report, organization_name, document.original_filename, generated_at
        )
        filename = f"due-diligence-{_safe_filename_stub(document.original_filename)}.md"
        return filename, content

    @staticmethod
    async def export_pdf(
        db: AsyncSession,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
        top_k: int = DEFAULT_RETRIEVAL_TOP_K,
    ) -> tuple[str, bytes]:
        """Generate a due diligence report and render it as a PDF.

        Calls `DueDiligenceService.generate_report` exactly once — no
        separate AI pipeline, no duplicate generation.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.
            top_k: The number of retrieved excerpts to use as context,
                passed through to `DueDiligenceService`.

        Returns:
            A tuple of `(filename, pdf_bytes)`.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization
                (propagated from `DueDiligenceService`).
            DocumentNotProcessedError: If the document's text extraction
                has not completed successfully (propagated from
                `DueDiligenceService`).
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured (propagated from `DueDiligenceService`).
            AIRequestFailedError: If report generation fails after
                retrying once (propagated from `DueDiligenceService`).
            InvalidAIResponseError: If the AI's response is invalid
                (propagated from `DueDiligenceService`).
            EmbeddingServiceNotConfiguredError: If no OpenAI API key is
                configured for embeddings (propagated from
                `DueDiligenceService`).
            EmbeddingRequestFailedError: If the retrieval query's
                embedding request fails (propagated from
                `DueDiligenceService`).
            InvalidEmbeddingDimensionError: If the retrieval query's
                embedding has the wrong dimensionality (propagated from
                `DueDiligenceService`).
            ReportRenderingFailedError: If PDF layout/rendering fails.
        """
        report = await DueDiligenceService.generate_report(
            db, document_id, actor_id, top_k
        )
        document = await DocumentService.get_document(db, document_id, actor_id)
        organization_name = await _fetch_organization_name(
            db, document.organization_id
        )
        generated_at = datetime.now(timezone.utc)

        pdf_bytes = render_pdf(
            report, organization_name, document.original_filename, generated_at
        )
        filename = (
            f"due-diligence-{_safe_filename_stub(document.original_filename)}.pdf"
        )
        return filename, pdf_bytes