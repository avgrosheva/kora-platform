"""Persistence and retrieval for time-series financial facts.

This is the thin ORM-facing layer that `derived_metrics_service.py`'s
pure calculators sit behind: it converts `FinancialFact` rows to/from
the DB-independent `FactPoint` representation, so calculators never
import SQLAlchemy.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_fact import (
    FinancialFact,
    FinancialMetricType,
    FinancialValueType,
    PeriodType,
)
from app.services.derived_metrics_service import FactPoint, facts_from_financial_facts


class FinancialFactsService:
    """Create, list, and convert `FinancialFact` rows for a document."""

    @staticmethod
    async def create_fact(
        db: AsyncSession,
        document_id: uuid.UUID,
        metric: FinancialMetricType,
        value: float,
        period_type: PeriodType,
        period: str | None,
        value_type: FinancialValueType,
        currency: str | None = None,
        source_citation_id: uuid.UUID | None = None,
    ) -> FinancialFact:
        """Persist a single financial fact.

        Args:
            db: The active database session.
            document_id: The document this fact was extracted from.
            metric: Which metric this is.
            value: The numeric value.
            period_type: The granularity of `period`.
            period: The specific period string, or `None`.
            value_type: Actual/forecast/target/estimate/derived.
            currency: The ISO 4217 currency code, or `None`.
            source_citation_id: The supporting citation's id, or `None`.

        Returns:
            The newly created `FinancialFact`.
        """
        fact = FinancialFact(
            document_id=document_id,
            metric=metric.value,
            value=value,
            currency=currency,
            period_type=period_type.value,
            period=period,
            value_type=value_type.value,
            source_citation_id=source_citation_id,
        )
        db.add(fact)
        await db.commit()
        await db.refresh(fact)
        return fact

    @staticmethod
    async def list_facts(db: AsyncSession, document_id: uuid.UUID) -> list[FinancialFact]:
        """Fetch all financial facts for a document.

        Args:
            db: The active database session.
            document_id: The document's id.

        Returns:
            All `FinancialFact` rows for the document, unordered.
        """
        result = await db.execute(
            select(FinancialFact).where(FinancialFact.document_id == document_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_fact_points(db: AsyncSession, document_id: uuid.UUID) -> list[FactPoint]:
        """Fetch a document's facts as DB-independent `FactPoint`s.

        This is the bridge into `derived_metrics_service.py` and
        `validation_service.py`, both of which operate purely on
        `FactPoint` lists.

        Args:
            db: The active database session.
            document_id: The document's id.

        Returns:
            The document's facts as `FactPoint`s.
        """
        rows = await FinancialFactsService.list_facts(db, document_id)
        return facts_from_financial_facts(rows)

    @staticmethod
    async def replace_facts(
        db: AsyncSession, document_id: uuid.UUID, facts: list[dict]
    ) -> list[FinancialFact]:
        """Replace all of a document's financial facts with a new set.

        Args:
            db: The active database session.
            document_id: The document whose facts are being replaced.
            facts: A list of dicts with keys matching `create_fact`'s
                parameters (minus `db`/`document_id`).

        Returns:
            The newly created `FinancialFact` rows.
        """
        await db.execute(delete(FinancialFact).where(FinancialFact.document_id == document_id))

        rows = [
            FinancialFact(
                document_id=document_id,
                metric=f["metric"].value if isinstance(f["metric"], FinancialMetricType) else f["metric"],
                value=f["value"],
                currency=f.get("currency"),
                period_type=f["period_type"].value if isinstance(f["period_type"], PeriodType) else f["period_type"],
                period=f.get("period"),
                value_type=f["value_type"].value if isinstance(f["value_type"], FinancialValueType) else f["value_type"],
                source_citation_id=f.get("source_citation_id"),
            )
            for f in facts
        ]
        db.add_all(rows)
        await db.commit()
        for row in rows:
            await db.refresh(row)
        return rows