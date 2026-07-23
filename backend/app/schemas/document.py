"""Pydantic schemas for the document ingestion and processing domain."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus

__all__ = [
    "DocumentStatus",
    "DocumentRead",
    "DocumentUploadResponse",
    "DocumentListResponse",
    "DocumentExtractionResult",
]


class DocumentRead(BaseModel):
    """Public representation of an uploaded document.

    Attributes:
        id: The document's unique identifier.
        organization_id: The organization this document belongs to.
        uploaded_by: The id of the user who uploaded the document.
        original_filename: The filename as supplied by the uploader.
        content_type: The MIME type of the uploaded file.
        size_bytes: The size of the file, in bytes.
        status: The document's current processing status.
        page_count: The number of pages in the source document, or
            `None` if not applicable or not yet processed.
        processing_error: The most recent processing error message, or
            `None` if processing has never failed.
        processed_at: Timestamp of the most recent processing attempt,
            or `None` if never processed.
        created_at: Timestamp when the document was uploaded.
        updated_at: Timestamp when the document record was last
            updated.

    Note:
        `text_content` is intentionally excluded from this schema, since
        extracted text can be arbitrarily large. It is stored on the
        `Document` model for future AI features to consume directly,
        rather than being serialized in every API response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    uploaded_by: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    page_count: int | None
    processing_error: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(DocumentRead):
    """Response returned immediately after a successful upload.

    Currently identical to `DocumentRead`; kept as a distinct type so
    the upload endpoint's response contract can evolve independently
    (e.g. to include processing hints) without affecting other reads.
    """


class DocumentListResponse(BaseModel):
    """Paginated-style response for listing an organization's documents.

    Attributes:
        items: The documents returned.
        total: The total number of documents in the list.
    """

    items: list[DocumentRead]
    total: int


class DocumentExtractionResult(BaseModel):
    """Result of extracting text content from a document file.

    Attributes:
        text: The extracted plain text content.
        page_count: The number of pages in the source document, or
            `None` for formats without a page concept (e.g. plain text).
        character_count: The total number of characters in `text`.
    """

    text: str
    page_count: int | None
    character_count: int