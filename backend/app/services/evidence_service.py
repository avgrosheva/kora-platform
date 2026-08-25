"""The canonical evidence-read facade for a document (Step 1 of the
Evidence Layer / Findings Layer initiative).

Today, "what do we know about this document?" is answered independently
by several services, each querying its own subset of tables directly
(`coverage_service.py` reads `financial_facts` and expects the caller to
have already computed `*_fields_found` sets from `DocumentAnalysis`;
`GET /documents/{id}/missing-information` currently hardcodes some of
those same sets to empty; `financial-analysis` and
`extract-financial-facts` write to two different tables that nothing
reconciles). That drift is the root cause of Bugs A and B in the
Evidence Layer plan: different features disagree about facts that are,
in reality, the same underlying data.

`EvidenceService` is the single facade every other service should call
to answer that question from now on. It does not introduce new storage
— `financial_facts` and `DocumentAnalysis` remain exactly as they are —
it only unifies the *read* path into one `EvidenceFact` shape, with one
place that decides which category a field belongs to.

Step 4 update: `qualitative_facts` (non-numeric, categorized claims —
customer/legal/operational/IP/team/market risk, and opportunities) is
now wired in alongside `financial_facts` and `DocumentAnalysis`. This is
also what retires the temporary category default this module used to
apply to `DocumentAnalysis.risks`/`opportunities` (see
`_ANALYSIS_ARRAY_FIELDS` below) — those two free-text columns are still
read (they remain the source for the plain, non-cited `/analyze`
pipeline, which does not produce `QualitativeFact` rows), but a document
that went through the cited pipeline now gets its risk/opportunity
evidence from the real, per-claim categorized `QualitativeFact` rows
instead, with `"company"` staying only as the fallback for the
un-categorizable free-text case.

Remaining out of scope (see the Evidence Layer plan for when it lands):
    - `financial_metrics` (the flat, single-period table) is NOT read
      here. Unifying the two financial-extraction pipelines was Step 3;
      `/financial-analysis` mirrors its mappable fields into
      `financial_facts` itself, so this facade already sees them with
      no further change needed here.
    - Per-citation confidence is not resolved into `EvidenceFact.confidence`
      for financial facts, since `FinancialFact` itself carries no
      confidence column (only `SourceCitation` does, and joining it in
      here would be a second responsibility better left to
      `citation_service.py`). `QualitativeFact` is different — it
      carries `confidence` directly, so that one *is* populated below.
"""

import enum
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_analysis import DocumentAnalysis
from app.models.financial_fact import FinancialMetricType, FinancialValueType
from app.models.qualitative_fact import (
    QualitativeFact,
    QualitativeFactCategory,
    QualitativeFactType,
)
from app.schemas.coverage import CoverageAssessmentResult
from app.services.coverage_service import (
    REQUIRED_COMPANY_FIELDS,
    REQUIRED_MARKET_FIELDS,
    compute_coverage,
)
from app.services.derived_metrics_service import FactPoint
from app.services.financial_facts_service import FinancialFactsService
from app.services.qualitative_facts_service import QualitativeFactsService


class EvidenceFactType(str, enum.Enum):
    """How a piece of evidence came to be known, per the project's
    "fact vs. calculated vs. inferred" distinction (see
    `financial_fact.py`'s `FinancialValueType.DERIVED` docstring for the
    precedent this follows).

    Attributes:
        DOCUMENT_STATED: Extracted directly from the source document
            (whether a plain scalar/array `DocumentAnalysis` field, or
            an `actual`/`forecast`/`target`/`estimate` `FinancialFact`).
            The AI performed extraction, not judgment, to produce it.
        DERIVED: Computed by Kora from other facts (mirrors
            `FinancialValueType.DERIVED` and, later, `DerivedMetric`
            rows) rather than stated verbatim by the source.
        AI_INFERRED: A conclusion the AI drew that goes beyond what the
            source document literally states. Nothing in this service
            currently produces `AI_INFERRED` facts — it is defined here
            because `EvidenceFact` and `Finding` (Step 5) share this
            enum, and inference-based findings must always be visibly
            labeled as such, never presented as document-stated.
    """

    DOCUMENT_STATED = "document_stated"
    DERIVED = "derived"
    AI_INFERRED = "ai_inferred"


@dataclass(frozen=True)
class EvidenceFact:
    """One normalized fact about a document, regardless of which table
    it physically lives in.

    Attributes:
        category: One of `"financial"`, `"company"`, `"market"`,
            `"team"` — matching `coverage_service.py`'s category keys
            exactly, so Coverage and Missing-Information (Step 2) can
            group facts the same way they already group their
            checklists. See module docstring on `_ANALYSIS_FIELD_CATEGORY`
            for how a `DocumentAnalysis` field's category is decided.
        field_name: The metric name (`FinancialMetricType.value`, e.g.
            `"revenue"`) or `DocumentAnalysis` attribute name (e.g.
            `"company_name"`). One flat namespace — the two sources
            never produce overlapping names.
        value: The raw value (`float` for financial facts, `str` or
            `list[str]` for analysis fields).
        display_value: A human-readable rendering of `value`, for UIs
            and chat answers that don't want to re-implement formatting.
        fact_type: How this fact came to be known (see
            `EvidenceFactType`).
        source_citation_id: The supporting `SourceCitation.id`, as a
            string, or `None` if this fact isn't yet linked to one.
        confidence: The extraction's confidence in this fact, or `None`
            if not available (see module docstring — not populated for
            financial facts today).
        period: The specific period this fact applies to (e.g.
            `"2025"`), or `None` for facts with no time dimension
            (every `DocumentAnalysis` field, and financial facts with
            `period_type=UNKNOWN`). Not part of the checklist "was this
            field ever found" question Coverage/Missing-Information ask
            (Step 2), but kept so a caller that needs to distinguish
            "2023 revenue" from "2025 revenue" — e.g. a future chat tool
            — doesn't lose that information by going through this
            facade.
    """

    category: str
    field_name: str
    value: Any
    display_value: str
    fact_type: EvidenceFactType
    source_citation_id: str | None
    confidence: float | None
    period: str | None = None


# ---------------------------------------------------------------------------
# Category assignment
# ---------------------------------------------------------------------------
#
# Financial facts always belong to the "financial" category — there is
# only one financial checklist (`FinancialMetricType` is a closed enum).
#
# DocumentAnalysis fields are less clear-cut: coverage_service.py's own
# registries are the existing source of truth for which category each
# checklist field belongs to, so this map is built FROM those registries
# rather than inventing a second, possibly-inconsistent classification.
# That is also what makes the Step 2 invariant possible at all: Coverage
# and Missing-Information will both derive their found/missing sets from
# this same map via EvidenceService, so they cannot drift apart again.
#
# `REQUIRED_COMPANY_FIELDS` and `REQUIRED_MARKET_FIELDS` both list
# "competitors" (a document can reasonably be asked about it from either
# angle). Since `EvidenceFact` needs exactly one category per field, the
# tie is broken in favor of "company" — `competitors` is a real
# `DocumentAnalysis` column and this is where it structurally lives; the
# `REQUIRED_MARKET_FIELDS` entries with no corresponding
# `DocumentAnalysis` column at all (`market_size`, `competitive_advantages`)
# still never produce an `EvidenceFact` from this map — `market_risks` is
# the one exception, produced instead from `QualitativeFact` rows below.
_ANALYSIS_FIELD_CATEGORY: dict[str, str] = {field: "company" for field in REQUIRED_COMPANY_FIELDS}
for _field in REQUIRED_MARKET_FIELDS:
    _ANALYSIS_FIELD_CATEGORY.setdefault(_field, "market")

# `risks` and `opportunities` are real DocumentAnalysis columns, still
# categorized "company" as a fallback — but this is no longer the
# primary way risk/opportunity evidence reaches this facade (see
# _QUALITATIVE_CATEGORY_TO_EVIDENCE_CATEGORY below, which replaces the
# temporary blanket default Step 1 used here). A document analyzed
# through the cited pipeline gets its risk/opportunity evidence from
# individually-categorized `QualitativeFact` rows instead; this fallback
# only still matters for documents analyzed through the plain, non-cited
# `/analyze` pipeline, which has no equivalent structured extraction and
# never will (it has no citations to hang a `QualitativeFact` off of).
_ANALYSIS_FIELD_CATEGORY.setdefault("risks", "company")
_ANALYSIS_FIELD_CATEGORY.setdefault("opportunities", "company")

# The scalar and array fields actually present on the DocumentAnalysis
# model — kept as an explicit, ordered list (rather than introspecting
# the ORM class's columns at runtime) so this file is the single place
# that has to change if that model's shape changes.
_ANALYSIS_SCALAR_FIELDS: tuple[str, ...] = ("company_name", "industry", "business_model", "summary")
_ANALYSIS_ARRAY_FIELDS: tuple[str, ...] = (
    "key_products",
    "revenue_streams",
    "customers",
    "competitors",
    "risks",
    "opportunities",
)


def _category_for_analysis_field(field_name: str) -> str:
    """Look up an analysis field's category, defaulting to "company".

    The default only matters for a field added to
    `_ANALYSIS_SCALAR_FIELDS`/`_ANALYSIS_ARRAY_FIELDS` without a matching
    entry above; every field currently listed has an explicit entry.
    """
    return _ANALYSIS_FIELD_CATEGORY.get(field_name, "company")


# `QualitativeFact.category` is a finer-grained taxonomy than
# `EvidenceFact.category`'s four coarse buckets — this maps one onto the
# other. `TEAM_RISK`/`MARKET_RISK` land on the matching coarse bucket
# directly; everything else (customer/legal/operational/IP risk,
# opportunities, and anything uncategorizable) falls back to "company",
# the same general bucket the old free-text risks/opportunities default
# used — the difference is this decision is now made per-claim, from
# real extracted content, not applied as a blanket default to an entire
# undifferentiated list.
_QUALITATIVE_CATEGORY_TO_EVIDENCE_CATEGORY: dict[QualitativeFactCategory, str] = {
    QualitativeFactCategory.CUSTOMER_RISK: "company",
    QualitativeFactCategory.LEGAL_REGULATORY: "company",
    QualitativeFactCategory.OPERATIONAL_DEPENDENCY: "company",
    QualitativeFactCategory.IP_OWNERSHIP: "company",
    QualitativeFactCategory.TEAM_RISK: "team",
    QualitativeFactCategory.MARKET_RISK: "market",
    QualitativeFactCategory.OPPORTUNITY: "company",
    QualitativeFactCategory.OTHER: "company",
}

# QualitativeFactType has no DERIVED member (nothing computes a
# qualitative claim the way a derived financial figure is computed), so
# this mapping is a straight 1:1 rename onto two of EvidenceFactType's
# three members.
_QUALITATIVE_FACT_TYPE_TO_EVIDENCE_FACT_TYPE: dict[str, EvidenceFactType] = {
    QualitativeFactType.DOCUMENT_STATED.value: EvidenceFactType.DOCUMENT_STATED,
    QualitativeFactType.AI_INFERRED.value: EvidenceFactType.AI_INFERRED,
}


# ---------------------------------------------------------------------------
# Pure normalization (no DB access — unit-testable in isolation)
# ---------------------------------------------------------------------------


def evidence_facts_from_financial_facts(facts: list[FactPoint]) -> list[EvidenceFact]:
    """Normalize a document's `FactPoint`s into `EvidenceFact`s.

    Args:
        facts: The document's financial facts, as returned by
            `FinancialFactsService.get_fact_points`.

    Returns:
        One `EvidenceFact` per input fact, always categorized
        `"financial"`.
    """
    return [
        EvidenceFact(
            category="financial",
            field_name=fact.metric.value,
            value=fact.value,
            display_value=_format_financial_value(fact),
            fact_type=(
                EvidenceFactType.DERIVED
                if fact.value_type == FinancialValueType.DERIVED
                else EvidenceFactType.DOCUMENT_STATED
            ),
            source_citation_id=fact.source_citation_id,
            confidence=None,
            period=fact.period,
        )
        for fact in facts
    ]


def _format_financial_value(fact: FactPoint) -> str:
    """Render a financial fact as a short human-readable string.

    Args:
        fact: The fact to format.

    Returns:
        E.g. `"$96,000,000 (2025)"` or `"620,000 (2025)"` for a
        currency-less count.
    """
    magnitude = f"{fact.value:,.2f}".rstrip("0").rstrip(".")
    amount = f"{fact.currency} {magnitude}" if fact.currency else magnitude
    return f"{amount} ({fact.period})" if fact.period else amount


def evidence_facts_from_analysis(analysis: DocumentAnalysis) -> list[EvidenceFact]:
    """Normalize a document's `DocumentAnalysis` row into `EvidenceFact`s.

    A field with a `None` value, an empty string, or an empty list
    produces no `EvidenceFact` — "found" here means the same thing it
    means to `coverage_service.py`: a real, non-empty extracted value.

    Args:
        analysis: The document's `DocumentAnalysis` row.

    Returns:
        One `EvidenceFact` per populated field, categorized per
        `_ANALYSIS_FIELD_CATEGORY`.
    """
    evidence: list[EvidenceFact] = []

    for field_name in _ANALYSIS_SCALAR_FIELDS:
        value = getattr(analysis, field_name)
        if not value or not str(value).strip():
            continue
        evidence.append(
            EvidenceFact(
                category=_category_for_analysis_field(field_name),
                field_name=field_name,
                value=value,
                display_value=str(value),
                fact_type=EvidenceFactType.DOCUMENT_STATED,
                source_citation_id=None,
                confidence=None,
            )
        )

    for field_name in _ANALYSIS_ARRAY_FIELDS:
        values = getattr(analysis, field_name)
        if not values:
            continue
        evidence.append(
            EvidenceFact(
                category=_category_for_analysis_field(field_name),
                field_name=field_name,
                value=list(values),
                display_value=", ".join(str(v) for v in values),
                fact_type=EvidenceFactType.DOCUMENT_STATED,
                source_citation_id=None,
                confidence=None,
            )
        )

    return evidence


def _field_name_for_qualitative_fact(fact: QualitativeFact) -> str:
    """Resolve a qualitative fact's `EvidenceFact.field_name`.

    `MARKET_RISK` is the one qualitative category with an unambiguous,
    word-for-word match to a specific `coverage_service.REQUIRED_MARKET_FIELDS`
    checklist item (`"market_risks"`) — a document with a real
    market-risk claim now satisfies that checklist item for the first
    time since nothing else in the pipeline ever produced it. No other
    category gets this treatment: `TEAM_RISK`, for instance, is broader
    than `REQUIRED_TEAM_FIELDS`' specific `"key_person_dependency"` item
    (a team-risk claim might be about hiring difficulty or turnover,
    not key-person dependency specifically), so mapping it onto that one
    named field would overclaim a match that isn't actually there.
    Categories without a clean checklist correspondence get a
    fact-unique field name instead — they still surface as evidence
    (via `EvidenceService.get_evidence`), just not as a specific
    checklist item Coverage/Missing-Information count.

    Args:
        fact: The qualitative fact.

    Returns:
        `"market_risks"` for a `MARKET_RISK` fact; otherwise a
        fact-unique, namespaced field name.
    """
    if fact.category == QualitativeFactCategory.MARKET_RISK.value:
        return "market_risks"
    return f"qualitative:{fact.category}:{fact.id}"


def evidence_facts_from_qualitative_facts(facts: list[QualitativeFact]) -> list[EvidenceFact]:
    """Normalize a document's `QualitativeFact` rows into `EvidenceFact`s.

    Args:
        facts: The document's qualitative facts, as returned by
            `QualitativeFactsService.list_facts`.

    Returns:
        One `EvidenceFact` per input fact, categorized per
        `_QUALITATIVE_CATEGORY_TO_EVIDENCE_CATEGORY`.
    """
    return [
        EvidenceFact(
            category=_QUALITATIVE_CATEGORY_TO_EVIDENCE_CATEGORY.get(
                QualitativeFactCategory(fact.category), "company"
            ),
            field_name=_field_name_for_qualitative_fact(fact),
            value=fact.claim_text,
            display_value=fact.claim_text,
            fact_type=_QUALITATIVE_FACT_TYPE_TO_EVIDENCE_FACT_TYPE.get(
                fact.fact_type, EvidenceFactType.DOCUMENT_STATED
            ),
            source_citation_id=str(fact.source_citation_id) if fact.source_citation_id else None,
            confidence=fact.confidence,
        )
        for fact in facts
    ]


def evidence_contains(evidence: list[EvidenceFact], field_name: str, category: str | None = None) -> bool:
    """Check whether a field is present in an already-fetched evidence list.

    A pure counterpart to `EvidenceService.has_fact`, for callers that
    already have an `EvidenceFact` list (e.g. after calling
    `EvidenceService.get_evidence` once for several checks) and want to
    avoid re-querying the database per field.

    Args:
        evidence: The evidence facts to search.
        field_name: The field to look for.
        category: If given, only a fact in this category counts as a
            match.

    Returns:
        `True` if a matching fact is present.
    """
    return any(
        fact.field_name == field_name and (category is None or fact.category == category) for fact in evidence
    )


# ---------------------------------------------------------------------------
# DB-facing facade
# ---------------------------------------------------------------------------


class EvidenceService:
    """The only interface other services should use to answer "what do
    we know about this document?"

    Physical storage stays split across `financial_facts` and
    `DocumentAnalysis` (and, from Step 4, `qualitative_facts`) — this
    class only unifies the read path.
    """

    @staticmethod
    async def get_evidence(
        db: AsyncSession, document_id: uuid.UUID, category: str | None = None
    ) -> list[EvidenceFact]:
        """Fetch and normalize everything known about a document.

        Args:
            db: The active database session.
            document_id: The document's id.
            category: If given, only facts in this category are
                returned (`"financial"`, `"company"`, `"market"`, or
                `"team"`).

        Returns:
            The document's evidence, normalized into `EvidenceFact`s.
            Empty if the document has no financial facts, no analysis,
            and no qualitative facts yet — this is a normal state (e.g.
            a freshly uploaded, unprocessed document), not an error.
        """
        facts = await FinancialFactsService.get_fact_points(db, document_id)
        evidence = evidence_facts_from_financial_facts(facts)

        result = await db.execute(select(DocumentAnalysis).where(DocumentAnalysis.document_id == document_id))
        analysis = result.scalar_one_or_none()
        if analysis is not None:
            evidence.extend(evidence_facts_from_analysis(analysis))

        qualitative_facts = await QualitativeFactsService.list_facts(db, document_id)
        evidence.extend(evidence_facts_from_qualitative_facts(qualitative_facts))

        if category is not None:
            evidence = [fact for fact in evidence if fact.category == category]

        return evidence

    @staticmethod
    async def has_fact(
        db: AsyncSession, document_id: uuid.UUID, field_name: str, category: str | None = None
    ) -> bool:
        """Check whether a specific field has been found for a document.

        Args:
            db: The active database session.
            document_id: The document's id.
            field_name: The metric or analysis field name to look for.
            category: If given, only a fact in this category counts.

        Returns:
            `True` if the field is present, regardless of which
            underlying table it came from.
        """
        evidence = await EvidenceService.get_evidence(db, document_id, category=category)
        return evidence_contains(evidence, field_name)

    @staticmethod
    async def fields_found(db: AsyncSession, document_id: uuid.UUID, category: str) -> set[str]:
        """Return the set of found field names for one category.

        This is the direct replacement for the `*_fields_found` sets
        `coverage_service.compute_coverage` and
        `missing_information_service.compute_missing_information` expect
        as arguments — both currently computed (or, for Bug B,
        hardcoded) independently by `app/api/v1/documents.py`. Step 2
        rewires both call sites to build those sets from this method
        instead.

        Args:
            db: The active database session.
            document_id: The document's id.
            category: The category to return found fields for.

        Returns:
            The set of `field_name`s found in that category.
        """
        evidence = await EvidenceService.get_evidence(db, document_id, category=category)
        return {fact.field_name for fact in evidence}

    @staticmethod
    async def get_coverage(db: AsyncSession, document_id: uuid.UUID) -> CoverageAssessmentResult:
        """Compute a document's coverage assessment.

        A second, independent caller of `coverage_service.compute_coverage`
        alongside `app/api/v1/documents.py`'s `get_document_coverage` —
        added for `investment_scoring_service.py`'s `assessment_status`
        threshold (Evidence Layer plan, Step 8), which needs overall
        coverage confidence as an input. Deliberately NOT wired back into
        `GET /{document_id}/coverage` itself in this step — that
        endpoint's existing wiring is left untouched, per Step 8's scope
        (Coverage is not being rewired here), so this duplicates a few
        lines from that endpoint rather than refactoring it.

        Args:
            db: The active database session.
            document_id: The document's id.

        Returns:
            The computed coverage assessment.
        """
        evidence = await EvidenceService.get_evidence(db, document_id)
        financial_metrics_found = {
            FinancialMetricType(fact.field_name) for fact in evidence if fact.category == "financial"
        }
        company_fields_found = {fact.field_name for fact in evidence if fact.category == "company"}
        market_fields_found = {fact.field_name for fact in evidence if fact.category == "market"}
        team_fields_found = {fact.field_name for fact in evidence if fact.category == "team"}

        return compute_coverage(
            financial_metrics_found=financial_metrics_found,
            company_fields_found=company_fields_found,
            market_fields_found=market_fields_found,
            team_fields_found=team_fields_found,
            citations_count=0,
            total_extracted_fields=(
                len(financial_metrics_found)
                + len(company_fields_found)
                + len(market_fields_found)
                + len(team_fields_found)
            ),
        )
