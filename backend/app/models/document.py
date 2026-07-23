"""SQLAlchemy ORM model for uploaded documents."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_analysis import DocumentAnalysis
    from app.models.financial_metrics import FinancialMetrics
    from app.models.organization import Organization
    from app.models.user import User


class DocumentStatus(str, enum.Enum):
    """Lifecycle status of an uploaded document.

    Attributes:
        UPLOADED: The file has been stored but not yet processed.
        PROCESSING: The document is currently having its text extracted.
        COMPLETED: Text extraction completed successfully.
        FAILED: Text extraction failed; see `Document.processing_error`.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """Represents a file uploaded to an organization.

    Covers ingestion (raw file storage) and text-extraction processing.
    No embeddings, vector search, or AI analysis is performed here —
    only plain text extraction, which future AI features will consume.

    Attributes:
        id: Primary key, a randomly generated UUID.
        organization_id: The organization this document belongs to.
        uploaded_by: The user who uploaded this document.
        filename: The generated, storage-safe filename (unique on disk).
        original_filename: The filename as supplied by the uploader.
        content_type: The MIME type of the uploaded file.
        size_bytes: The size of the file, in bytes.
        storage_key: The relative path/key used to locate the file
            within the configured storage backend.
        status: The document's current processing status.
        text_content: The extracted plain text, or `None` if processing
            has not completed successfully.
        page_count: The number of pages in the source document, or
            `None` for formats without a page concept, or if processing
            has not completed.
        processing_error: A human-readable description of the most
            recent processing failure, or `None` if processing has
            never failed.
        processed_at: Timezone-aware timestamp of the most recent
            processing attempt (success or failure), or `None` if never
            processed.
        created_at: Timezone-aware timestamp when the record was
            created.
        updated_at: Timezone-aware timestamp when the record was last
            updated.
        organization: The related `Organization`.
        uploader: The related `User` who uploaded the document.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(
        String(1024),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            native_enum=False,
            validate_strings=True,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        server_default=DocumentStatus.UPLOADED.value,
        index=True,
    )
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    analysis: Mapped["DocumentAnalysis | None"] = relationship(
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )

    financial_metrics: Mapped["FinancialMetrics | None"] = relationship(
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )

    organization: Mapped["Organization"] = relationship(back_populates="documents")
    uploader: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the document.

        Returns:
            A string identifying the document by id and original
            filename.
        """
        return f"<Document id={self.id} original_filename={self.original_filename!r}>"