"""Persistence and retrieval for source-provenance citations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.source_citation import SourceCitation


class CitationService:
    """Create and retrieve `SourceCitation` rows for a document."""

    @staticmethod
    async def create_citation(
        db: AsyncSession,
        document_id: uuid.UUID,
        field_path: str,
        quote: str,
        page_number: int | None = None,
        chunk_id: uuid.UUID | None = None,
        confidence: float | None = None,
        extraction_version: str | None = None,
    ) -> SourceCitation:
        """Persist a single source citation.

        Args:
            db: The active database session.
            document_id: The document this citation belongs to.
            field_path: The extracted field this citation supports.
            quote: The exact supporting passage.
            page_number: The source page number, or `None`.
            chunk_id: The supporting `DocumentEmbedding` chunk's id, or
                `None`.
            confidence: The extraction's confidence in this citation,
                or `None`.
            extraction_version: A version tag for the extraction logic,
                or `None`.

        Returns:
            The newly created `SourceCitation`.
        """
        citation = SourceCitation(
            document_id=document_id,
            field_path=field_path,
            page_number=page_number,
            chunk_id=chunk_id,
            quote=quote,
            confidence=confidence,
            extraction_version=extraction_version,
        )
        db.add(citation)
        await db.commit()
        await db.refresh(citation)
        return citation

    @staticmethod
    async def list_citations(
        db: AsyncSession, document_id: uuid.UUID, field_path: str | None = None
    ) -> list[SourceCitation]:
        """Fetch citations for a document, optionally filtered by field.

        Args:
            db: The active database session.
            document_id: The document's id.
            field_path: If provided, only citations for this exact
                field path are returned.

        Returns:
            The matching `SourceCitation` rows.
        """
        stmt = select(SourceCitation).where(SourceCitation.document_id == document_id)
        if field_path is not None:
            stmt = stmt.where(SourceCitation.field_path == field_path)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def resolve_citation(db: AsyncSession, citation_id: uuid.UUID) -> dict | None:
        """Resolve a citation to its full display context.

        Args:
            db: The active database session.
            citation_id: The citation's id.

        Returns:
            A dict with `document_name`, `page_number`, and `quote`, or
            `None` if the citation does not exist.
        """
        result = await db.execute(
            select(SourceCitation, Document.original_filename)
            .join(Document, Document.id == SourceCitation.document_id)
            .where(SourceCitation.id == citation_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        citation, document_name = row
        return {
            "document_name": document_name,
            "page_number": citation.page_number,
            "quote": citation.quote,
        }