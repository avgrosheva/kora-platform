"""Document text-extraction pipeline.

Implements the processing flow that runs after a document has been
uploaded: determining the file type, extracting its plain text content,
and recording the result (or failure) on the `Document` record. This is
intentionally synchronous, in-process, and worker-free — no Celery, no
background jobs — matching the project's current infrastructure. It is
the seam future AI features (embeddings, RAG) will build on top of.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import anyio
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.storage import StorageService
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentExtractionResult

logger = get_logger(__name__)

_PDF_CONTENT_TYPE = "application/pdf"
_TXT_CONTENT_TYPE = "text/plain"


class DocumentProcessingError(Exception):
    """Base exception for document processing failures."""


class UnsupportedDocumentFormatError(DocumentProcessingError):
    """Raised when a document's content type has no text extractor."""


class TextExtractionError(DocumentProcessingError):
    """Raised when a document's file cannot be read or parsed."""


def _extract_pdf_text_sync(file_path: Path) -> DocumentExtractionResult:
    """Extract text from a PDF file, synchronously.

    Args:
        file_path: The absolute path to the PDF file.

    Returns:
        The extraction result, with `page_count` set to the PDF's page
        count.

    Raises:
        TextExtractionError: If the file cannot be opened or parsed as
            a PDF.
    """
    try:
        reader = PdfReader(str(file_path))
    except Exception as exc:
        raise TextExtractionError(f"Could not open PDF file: {exc}") from exc

    try:
        page_texts = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise TextExtractionError(
            f"Could not extract text from PDF: {exc}"
        ) from exc

    text = "\n\n".join(page_texts)
    return DocumentExtractionResult(
        text=text,
        page_count=len(reader.pages),
        character_count=len(text),
    )


def _extract_txt_text_sync(file_path: Path) -> DocumentExtractionResult:
    """Read a plain text file as UTF-8, synchronously.

    Args:
        file_path: The absolute path to the TXT file.

    Returns:
        The extraction result. `page_count` is always `None`, since
        plain text has no page concept.

    Raises:
        TextExtractionError: If the file is not valid UTF-8, or cannot
            be read.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise TextExtractionError(
            "TXT file is not valid UTF-8 encoded text."
        ) from exc
    except OSError as exc:
        raise TextExtractionError(f"Could not read TXT file: {exc}") from exc

    return DocumentExtractionResult(
        text=text,
        page_count=None,
        character_count=len(text),
    )


_EXTRACTORS: dict[str, Callable[[Path], DocumentExtractionResult]] = {
    _PDF_CONTENT_TYPE: _extract_pdf_text_sync,
    _TXT_CONTENT_TYPE: _extract_txt_text_sync,
}


async def extract_text(content_type: str, file_path: Path) -> DocumentExtractionResult:
    """Extract plain text from a stored file, dispatching by content type.

    Blocking I/O and parsing work is run in a worker thread via
    `anyio.to_thread.run_sync`, so it does not block the event loop.

    Args:
        content_type: The document's MIME type (e.g. `"application/pdf"`).
        file_path: The absolute path to the stored file.

    Returns:
        The extraction result.

    Raises:
        UnsupportedDocumentFormatError: If `content_type` has no
            registered extractor (currently only PDF and TXT are
            supported).
        TextExtractionError: If the file exists but cannot be read or
            parsed.
    """
    extractor = _EXTRACTORS.get(content_type)
    if extractor is None:
        raise UnsupportedDocumentFormatError(
            f"Text extraction is not supported for content type "
            f"'{content_type}'. Supported types: "
            f"{', '.join(_EXTRACTORS)}."
        )

    return await anyio.to_thread.run_sync(extractor, file_path)


class DocumentProcessorService:
    """Runs the extraction pipeline against an already-fetched document.

    This service performs no organization-membership or permission
    checks — those are the responsibility of `DocumentService`, which
    fetches the document (enforcing access control) before delegating
    here.
    """

    @staticmethod
    async def process_document(
        db: AsyncSession,
        storage: StorageService,
        document: Document,
    ) -> Document:
        """Run the full processing pipeline for a document.

        Transitions the document through `PROCESSING`, then to either
        `COMPLETED` (with `text_content` and `page_count` populated) or
        `FAILED` (with `processing_error` populated). Every transition
        is committed immediately, so the document's status is visible
        to other requests while processing is in progress.

        Args:
            db: The active database session.
            storage: The storage backend the file is persisted in.
            document: The document to process.

        Returns:
            The updated `Document`, reflecting either successful
            completion or a recorded failure. This method does not
            raise on extraction failure — failures are captured on the
            document record itself, per the required processing flow.
        """
        document.status = DocumentStatus.PROCESSING
        document.processing_error = None
        await db.commit()
        await db.refresh(document)

        file_path = storage.get_path(document.storage_key)

        try:
            result = await extract_text(document.content_type, file_path)
        except DocumentProcessingError as exc:
            logger.warning(
                "Document %s processing failed: %s", document.id, exc
            )
            return await _mark_failed(db, document, str(exc))
        except Exception as exc:  # noqa: BLE001 - intentional: any failure must be recorded, not propagated
            logger.exception(
                "Unexpected error processing document %s", document.id
            )
            return await _mark_failed(
                db, document, f"Unexpected processing error: {exc}"
            )

        document.text_content = result.text
        document.page_count = result.page_count
        document.status = DocumentStatus.COMPLETED
        document.processed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(document)
        return document


async def _mark_failed(db: AsyncSession, document: Document, error: str) -> Document:
    """Persist a processing failure onto a document record.

    Args:
        db: The active database session.
        document: The document that failed processing.
        error: A human-readable description of the failure.

    Returns:
        The updated `Document`, with `status=FAILED`.
    """
    document.status = DocumentStatus.FAILED
    document.processing_error = error
    document.processed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(document)
    return document