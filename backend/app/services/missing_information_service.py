"""Missing-information checklist framework (Section 10).

Evaluates a document against a fixed, configurable checklist of fields
a thorough due-diligence analysis should contain, reusing the same
required-field registries `coverage_service.py` defines rather than
maintaining a second parallel list. This is the engine that powers
`GET /documents/{id}/checks`'s missing-data summary, and will later
feed due-diligence founder-question generation (Section 7) and chat's
`get_missing_information` tool (Section 8) — both consume this
service's output rather than re-deriving it independently.

Field detection here is deliberately simple and deterministic: a field
is FOUND if a corresponding fact/analysis value exists and is non-null,
MISSING otherwise. AMBIGUOUS and CONTRADICTORY statuses are reserved
for future wiring once multi-document cross-referencing exists (Section
8's "compare multiple documents and find contradictions") — until then,
every field this service evaluates resolves to FOUND, MISSING, or
NOT_APPLICABLE only, and that limitation is stated explicitly rather
than faked.
"""

import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_fact import FinancialMetricType as M
from app.models.missing_information_item import MissingInformationItem
from app.schemas.missing_information import (
    ChecklistItemResult,
    FieldStatus,
    MissingInformationByCategory,
    MissingInformationResponse,
)
from app.services.coverage_service import (
    REQUIRED_COMPANY_FIELDS,
    REQUIRED_FINANCIAL_METRICS,
    REQUIRED_MARKET_FIELDS,
    REQUIRED_TEAM_FIELDS,
)
from app.services.derived_metrics_service import FactPoint

# Additional checklist categories beyond what coverage_service.py's
# per-field-count scoring needs — these are structural/legal/
# investment-specific fields with no corresponding FinancialMetricType
# or DocumentAnalysis field yet, so they are always MISSING until a
# real data source for them exists (cap table extraction, legal
# document parsing, etc. — none of which are in scope for this
# platform today). Listing them here, always-missing, is itself
# useful signal per the spec ("report... missing"), not a placeholder
# to hide.
INVESTMENT_FIELDS = ["cap_table", "ownership", "round_terms", "pre_money_valuation", "use_of_funds"]
LEGAL_FIELDS = ["material_litigation", "licenses", "ip_ownership", "data_privacy", "regulatory_risks"]
CUSTOMER_DETAIL_FIELDS = ["retention", "churn", "concentration", "cohorts", "nps", "repeat_rate"]


def compute_missing_information(
    financial_metrics_found: set[M],
    company_fields_found: set[str],
    market_fields_found: set[str],
    team_fields_found: set[str],
    customer_detail_fields_found: set[str] | None = None,
    investment_fields_found: set[str] | None = None,
    legal_fields_found: set[str] | None = None,
) -> MissingInformationResponse:
    """Evaluate a document against the full checklist.

    Args:
        financial_metrics_found: Which `REQUIRED_FINANCIAL_METRICS`
            were found (from `financial_facts`).
        company_fields_found: Which `REQUIRED_COMPANY_FIELDS` were
            found (from `DocumentAnalysis`).
        market_fields_found: Which `REQUIRED_MARKET_FIELDS` were found.
        team_fields_found: Which `REQUIRED_TEAM_FIELDS` were found
            (expected empty given no team-extraction capability).
        customer_detail_fields_found: Which `CUSTOMER_DETAIL_FIELDS`
            were found, or `None` (treated as none found).
        investment_fields_found: Which `INVESTMENT_FIELDS` were found,
            or `None`.
        legal_fields_found: Which `LEGAL_FIELDS` were found, or `None`.

    Returns:
        The full checklist evaluation, with items grouped by category.
    """
    customer_detail_fields_found = customer_detail_fields_found or set()
    investment_fields_found = investment_fields_found or set()
    legal_fields_found = legal_fields_found or set()

    category_registries: dict[str, tuple[list, set]] = {
        "company": (REQUIRED_COMPANY_FIELDS, company_fields_found),
        "financial": ([m.value for m in REQUIRED_FINANCIAL_METRICS], {m.value for m in financial_metrics_found}),
        "market": (REQUIRED_MARKET_FIELDS, market_fields_found),
        "team": (REQUIRED_TEAM_FIELDS, team_fields_found),
        "customers": (CUSTOMER_DETAIL_FIELDS, customer_detail_fields_found),
        "investment": (INVESTMENT_FIELDS, investment_fields_found),
        "legal": (LEGAL_FIELDS, legal_fields_found),
    }

    items: list[ChecklistItemResult] = []
    for category, (required_fields, found_fields) in category_registries.items():
        for field_name in required_fields:
            status = FieldStatus.FOUND if field_name in found_fields else FieldStatus.MISSING
            items.append(ChecklistItemResult(category=category, field_name=field_name, status=status))

    by_category = [
        MissingInformationByCategory(
            category=category,
            missing=[i.field_name for i in items if i.category == category and i.status == FieldStatus.MISSING],
            ambiguous=[i.field_name for i in items if i.category == category and i.status == FieldStatus.AMBIGUOUS],
            contradictory=[i.field_name for i in items if i.category == category and i.status == FieldStatus.CONTRADICTORY],
        )
        for category in category_registries
    ]

    return MissingInformationResponse(
        items=items,
        by_category=by_category,
        total_required=len(items),
        total_found=sum(1 for i in items if i.status == FieldStatus.FOUND),
    )


def facts_to_metric_set(facts: list[FactPoint]) -> set[M]:
    """Extract the distinct set of metrics present in a fact list.

    Args:
        facts: The document's financial facts.

    Returns:
        The set of `FinancialMetricType`s that have at least one fact.
    """
    return {f.metric for f in facts}


class MissingInformationService:
    """Persists and retrieves missing-information checklist results."""

    @staticmethod
    async def persist_items(
        db: AsyncSession, document_id: uuid.UUID, result: MissingInformationResponse
    ) -> list[MissingInformationItem]:
        """Replace a document's checklist items with newly computed ones.

        Args:
            db: The active database session.
            document_id: The document these items belong to.
            result: The computed checklist result.

        Returns:
            The newly persisted `MissingInformationItem` rows.
        """
        await db.execute(
            delete(MissingInformationItem).where(MissingInformationItem.document_id == document_id)
        )

        rows = [
            MissingInformationItem(
                document_id=document_id,
                category=item.category,
                field_name=item.field_name,
                status=item.status.value if hasattr(item.status, "value") else item.status,
            )
            for item in result.items
        ]
        db.add_all(rows)
        await db.commit()
        for row in rows:
            await db.refresh(row)
        return rows