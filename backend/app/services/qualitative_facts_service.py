"""Persistence and retrieval for non-numeric qualitative facts.

Mirrors `financial_facts_service.py`'s role: a thin ORM-facing layer
between the cited business-analysis extraction and the database. Unlike
`FinancialFactsService`, there is only ever one writer of
`qualitative_facts` (the cited pipeline in `document_analysis_service.py`
— there is no second, flat pipeline for qualitative claims the way
`financial_metrics` exists alongside `financial_facts`), so a plain
replace-on-rerun (matching `FinancialFactsService.replace_facts`, not
the metric-scoped `replace_facts_for_metrics`) is the correct and
sufficient semantics here.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qualitative_fact import (
    QualitativeFact,
    QualitativeFactCategory,
    QualitativeFactSeverityHint,
    QualitativeFactType,
)


class QualitativeFactsService:
    """Create, list, and replace `QualitativeFact` rows for a document."""

    @staticmethod
    async def list_facts(db: AsyncSession, document_id: uuid.UUID) -> list[QualitativeFact]:
        """Fetch all qualitative facts for a document.

        Args:
            db: The active database session.
            document_id: The document's id.

        Returns:
            All `QualitativeFact` rows for the document, unordered.
        """
        result = await db.execute(
            select(QualitativeFact).where(QualitativeFact.document_id == document_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def replace_facts(
        db: AsyncSession, document_id: uuid.UUID, facts: list[dict]
    ) -> list[QualitativeFact]:
        """Replace all of a document's qualitative facts with a new set.

        Args:
            db: The active database session.
            document_id: The document whose facts are being replaced.
            facts: A list of dicts with keys `category`, `claim_text`,
                `fact_type`, `severity_hint` (optional), `confidence`
                (optional), and `source_citation_id` (optional).

        Returns:
            The newly created `QualitativeFact` rows.
        """
        await db.execute(delete(QualitativeFact).where(QualitativeFact.document_id == document_id))

        rows = [
            QualitativeFact(
                document_id=document_id,
                category=(
                    f["category"].value
                    if isinstance(f["category"], QualitativeFactCategory)
                    else f["category"]
                ),
                claim_text=f["claim_text"],
                fact_type=(
                    f["fact_type"].value if isinstance(f["fact_type"], QualitativeFactType) else f["fact_type"]
                ),
                severity_hint=(
                    f["severity_hint"].value
                    if isinstance(f.get("severity_hint"), QualitativeFactSeverityHint)
                    else f.get("severity_hint")
                ),
                confidence=f.get("confidence"),
                source_citation_id=f.get("source_citation_id"),
            )
            for f in facts
        ]
        db.add_all(rows)
        await db.commit()
        for row in rows:
            await db.refresh(row)
        return rows
