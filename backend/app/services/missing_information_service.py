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

# What to ask for, and why it matters, per checklist field name (Evidence
# Layer plan, Step 9). Deliberately generic across ANY document — these
# describe the FIELD, not a specific company's data (a field that's
# actually MISSING has no extracted value to reference in the first
# place; see due_diligence_v2_service.py's founder-question generation
# for where a real extracted value IS referenced, when one exists).
_RECOMMENDED_REQUESTS: dict[str, str] = {
    # Financial (FinancialMetricType values)
    "revenue": "Request historical revenue by period; needed to assess scale and trajectory.",
    "gross_margin": "Request gross margin by period; needed to assess unit economics and scalability.",
    "ebitda": "Request EBITDA by period; needed to assess operating profitability.",
    "net_income": "Request net income by period; needed to assess bottom-line profitability after all expenses.",
    "cash": "Request current cash on hand; needed to assess near-term solvency.",
    "debt": "Request outstanding debt and terms; needed to assess leverage and repayment obligations.",
    "burn_rate": "Request monthly burn rate; needed to assess runway and capital efficiency.",
    "cac": "Request customer acquisition cost; needed to assess go-to-market efficiency.",
    "ltv": "Request customer lifetime value (or the inputs to calculate it); needed to assess unit economics alongside CAC.",
    "funding_amount": "Request total funding raised to date, by round; needed to assess capital history and dilution.",
    # Company
    "company_name": "Confirm the legal company name.",
    "industry": "Confirm the industry/category the company operates in; needed for market context.",
    "business_model": "Request a description of how the company generates revenue.",
    "summary": "Request a company overview if not already provided.",
    "key_products": "Request a list of key products or services.",
    "revenue_streams": "Request a breakdown of distinct revenue streams.",
    "customers": "Request a description of the target customer segment(s).",
    "competitors": "Request a list of known competitors.",
    # Market
    "market_size": "Request the addressable market size (TAM/SAM/SOM) and its source; needed to assess growth ceiling.",
    "competitive_advantages": "Request a description of durable competitive advantages (moat).",
    "market_risks": "Ask directly about known market risks (regulatory, competitive, macro).",
    # Team
    "founders": "Request founder names and backgrounds; needed to assess founder-market fit.",
    "key_executives": "Request key executive names and backgrounds.",
    "headcount": "Request current headcount, ideally by function.",
    "hiring_plan": "Request near-term hiring plans and key open roles.",
    "key_person_dependency": "Ask directly whether the business depends critically on any single individual.",
    # Customer detail
    "retention": "Request customer/revenue retention rates over time; needed to assess durability of revenue.",
    "churn": "Request churn rate by period; needed to assess customer durability.",
    "concentration": "Request the percentage of revenue from the largest customer(s); needed to assess concentration risk.",
    "cohorts": "Request cohort retention data; needed to assess whether unit economics improve or decay over time.",
    "nps": "Request Net Promoter Score or another customer satisfaction metric, if tracked.",
    "repeat_rate": "Request repeat purchase/usage rate, if applicable to the business model.",
    # Investment
    "cap_table": "Request a fully-diluted cap table; needed to assess ownership, dilution, and existing investor rights.",
    "ownership": "Request a breakdown of current ownership by stakeholder.",
    "round_terms": "Request the terms of the current or most recent funding round.",
    "pre_money_valuation": "Request the pre-money valuation for the current or most recent round.",
    "use_of_funds": "Request a breakdown of intended use of funds for this raise.",
    # Legal
    "material_litigation": "Ask directly whether the company is party to any material litigation.",
    "licenses": "Request confirmation of required licenses or regulatory approvals held.",
    "ip_ownership": "Request confirmation that IP is assigned to the company, including from contractors/co-founders.",
    "data_privacy": "Request a description of data privacy/compliance practices (e.g. GDPR, CCPA) if relevant.",
    "regulatory_risks": "Ask directly about known regulatory risks or pending regulatory changes affecting the business.",
}


def get_recommended_request(field_name: str) -> str | None:
    """Look up what to ask for, and why, for a given checklist field.

    Args:
        field_name: The checklist field name (e.g. `"cap_table"`).

    Returns:
        The recommended request text, or `None` if the field has none
        registered (should not happen for any field in the registries
        above — this is a safe fallback, not an expected path).
    """
    return _RECOMMENDED_REQUESTS.get(field_name)


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
            recommended_request = None if status == FieldStatus.FOUND else get_recommended_request(field_name)
            items.append(
                ChecklistItemResult(
                    category=category, field_name=field_name, status=status,
                    recommended_request=recommended_request,
                )
            )

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