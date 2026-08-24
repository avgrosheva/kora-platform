"""SQLAlchemy ORM model for the missing-information checklist framework."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class FieldStatus(str, enum.Enum):
    """The status of a single checklist field for a document.

    Attributes:
        FOUND: The field was clearly present in the source material.
        MISSING: The field was not found at all.
        AMBIGUOUS: Something relevant was found, but it's unclear or
            incomplete enough that it shouldn't be treated as reliably
            found.
        CONTRADICTORY: Conflicting values were found for this field
            (e.g. across multiple documents — full cross-document
            support is a later phase; single-document contradictions
            are detected where possible).
        NOT_APPLICABLE: This field does not apply to this company/deal
            (e.g. cap table fields for a document that is not a
            fundraising document).
    """

    FOUND = "found"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    CONTRADICTORY = "contradictory"
    NOT_APPLICABLE = "not_applicable"


class MissingInformationItem(Base):
    """A single checklist field's status for a document.

    One row per (document, field_name) pair, regenerated on each
    coverage run rather than accumulated indefinitely.

    Attributes:
        id: Primary key, a randomly generated UUID.
        document_id: The document this checklist item applies to.
        category: The checklist category (e.g. `"financial"`,
            `"team"`, `"investment"`), matching
            `coverage_service.REQUIRED_FIELDS_REGISTRY`'s top-level
            keys.
        field_name: The specific field within that category (e.g.
            `"cap_table"`, `"founding_year"`).
        status: Whether this field was found, missing, ambiguous,
            contradictory, or not applicable.
        created_at: Timezone-aware timestamp when this item was
            recorded.
        document: The related `Document`.
    """

    __tablename__ = "missing_information_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[FieldStatus] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="missing_information_items")

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the item.

        Returns:
            A string identifying the item by document id, category,
            and field name.
        """
        return (
            f"<MissingInformationItem document_id={self.document_id} "
            f"category={self.category} field_name={self.field_name!r}>"
        )