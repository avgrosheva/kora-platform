"""Financial intelligence orchestration.

Converts a document's persisted `DocumentAnalysis` (and underlying text)
into structured financial KPIs via `AIService`, normalizes the raw
extraction, computes derived metrics, and persists the result. Services
operate directly on `AsyncSession` — there is no repository layer in
this project's architecture.

Design note on data types: `FinancialMetrics` stores all figures as
plain floats rather than `Decimal`. This is a deliberate choice for this
layer — these are AI-extracted, approximate business intelligence
figures for dashboards and trend analysis, not accounting-grade ledger
entries. Floats serialize directly to JSON with no additional
transformation, which is what "future compatibility" with dashboard
endpoints requires.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_fact import FinancialMetricType, FinancialValueType, PeriodType
from app.models.financial_metrics import FinancialMetrics
from app.schemas.financial_metrics import FinancialMetricsCreate
from app.services.ai_service import AIService, FinancialExtractionResult
from app.services.document_analysis_service import (
    AnalysisNotFoundError,
    DocumentAnalysisService,
)
from app.services.document_service import DocumentNotFoundError, DocumentService

from app.services.ai_service import AIService, EXTRACTION_VERSION
from app.services.citation_service import CitationService
from app.services.financial_facts_service import FinancialFactsService

_EXTRACTABLE_FIELD_NAMES = (
    "revenue",
    "arr",
    "mrr",
    "gross_margin",
    "ebitda",
    "burn_rate",
    "cash",
    "customers",
    "growth_rate",
    "cac",
    "ltv",
    "valuation",
)

# Which FinancialMetricsCreate fields also get mirrored into
# financial_facts, and as which FinancialMetricType (Bug A fix — see
# _facts_from_flat_metrics). Deliberately NOT every extractable field:
#
#   - arr, mrr now have a corresponding FinancialMetricType (ARR, MRR —
#     added alongside the arr/mrr cited-pipeline 502 fix, see
#     ai_service.py's _CITED_FINANCIAL_SYSTEM_PROMPT), but are still
#     deliberately NOT mirrored here. `_normalize_and_compute` above
#     cross-derives arr from mrr*12 (or mrr from arr/12) whenever the
#     model only stated one of the two, and by the time a
#     FinancialMetricsCreate reaches this module there is no way to
#     tell a cross-derived value apart from a directly AI-stated one.
#     Mirroring it here would tag a Kora-computed number as
#     value_type=ACTUAL ("directly reported"), which is exactly the
#     class of mislabeling bug the gross_margin unit-convention fix
#     above was written to catch. If arr/mrr mirroring is wanted later,
#     `_normalize_and_compute` needs to surface which of the two was
#     cross-derived so this function can tag it DERIVED, not ACTUAL —
#     its own change, not a side effect of this fix.
#   - growth_rate still has no corresponding FinancialMetricType. It is
#     a calculated rate, not a raw stated figure — the kind of value
#     this project's convention keeps out of FinancialFact entirely,
#     as a DerivedMetric instead (see FinancialMetricType's docstring).
#     Left unmapped, not a gap.
#   - customers and valuation DO have plausible-looking targets
#     (REGISTERED_CUSTOMERS, VALUATION_POST_MONEY), but the flat
#     schema's "customers"/"valuation" fields are looser than what those
#     specific metric types mean in the canonical, citation-backed
#     extraction prompt (e.g. REGISTERED_CUSTOMERS is explicitly
#     distinguished from MONTHLY_ACTIVE_USERS there; a flat "customers"
#     count could be either, or neither, depending on the document).
#     Mapping them here would risk mislabeling data with a false-precise
#     metric type. Left unmapped rather than guessed.
#
# The seven mapped below have an unambiguous 1:1 meaning in both
# schemas, which is what makes mirroring them safe.
_FLAT_FIELD_TO_METRIC_TYPE: dict[str, FinancialMetricType] = {
    "revenue": FinancialMetricType.REVENUE,
    "gross_margin": FinancialMetricType.GROSS_MARGIN,
    "ebitda": FinancialMetricType.EBITDA,
    "burn_rate": FinancialMetricType.BURN_RATE,
    "cash": FinancialMetricType.CASH,
    "cac": FinancialMetricType.CAC,
    "ltv": FinancialMetricType.LTV,
}

# Unit-convention fix (found live, on a real document, after Step 3
# shipped): the flat schema's own convention states percentages as
# plain numbers ("gross_margin and growth_rate are percentages
# expressed as plain numbers (e.g. 42.5 for 42.5%), not fractions" --
# see _FINANCIAL_SYSTEM_PROMPT in ai_service.py). `financial_facts`,
# however, already has an established fraction convention for
# percentage-like metrics (0.425 for 42.5%) -- set by the citation-backed
# pipeline and load-bearing in two other places that predate this
# mirror entirely: validation_service.py's check_percentages_out_of_bounds
# (expects -1.0..1.5) and derived_metrics_service.py's
# _gross_profit_estimate_series ("Revenue x Gross Margin", which is only
# dimensionally correct if Gross Margin is a fraction — with the flat
# convention's raw "71", that formula silently computes a gross profit
# 100x too large, not just a display glitch). Converting the *other*
# convention (changing validation_service.py's threshold instead) would
# leave that gross-profit estimate broken for every flat-mirrored
# document, which is worse than the false-positive warning being fixed
# here — so the mirror is what gets normalized, not the established
# convention it's joining.
_FRACTION_CONVERTED_FIELDS = frozenset({"gross_margin"})


def _normalize_flat_value(field_name: str, value: float) -> float:
    """Convert one flat-schema value into `financial_facts`' unit convention.

    Args:
        field_name: The `FinancialMetricsCreate` field name.
        value: The raw flat-schema value.

    Returns:
        `value / 100` for fields in `_FRACTION_CONVERTED_FIELDS`
        (percentage-like metrics); `value` unchanged for everything else
        (dollar-amount fields need no conversion).
    """
    if field_name in _FRACTION_CONVERTED_FIELDS:
        return value / 100
    return value


def _facts_from_flat_metrics(metrics_data: FinancialMetricsCreate) -> list[dict]:
    """Mirror a flat extraction's mappable fields into `financial_facts` dicts.

    This is the Bug A fix: `/financial-analysis` previously only wrote
    `FinancialMetrics` (a single flat row), which Coverage, derived
    metrics, and validation never read (they read `financial_facts`
    exclusively) — so a document could show fully-populated financial
    KPIs in the Financials tab while Coverage reported 0/10. Mirroring
    the mappable fields here means the one existing user action
    (`POST /financial-analysis`) now produces both outputs, with no
    second AI call and no new user-facing step.

    Percentage-like fields (currently just `gross_margin`) are converted
    from the flat schema's plain-number convention to `financial_facts`'
    established fraction convention via `_normalize_flat_value` — see
    that function and `_FRACTION_CONVERTED_FIELDS` for why.

    The flat extraction has no period breakdown or forecast/actual
    distinction at all (unlike the citation-backed time-series
    extraction), so every mirrored fact is recorded as
    `period_type=UNKNOWN`/`period=None`/`value_type=ACTUAL` — the most
    honest available characterization of "a currently-stated figure with
    no further time context," not a claim that it's a specific period's
    actual result.

    Args:
        metrics_data: The just-computed, normalized flat extraction.

    Returns:
        One dict (matching `FinancialFactsService.replace_facts_for_metrics`'s
        `facts` shape) per populated, mappable field. No
        `source_citation_id` — the flat pipeline has no quote to cite.
    """
    return [
        {
            "metric": metric_type,
            "value": _normalize_flat_value(field_name, getattr(metrics_data, field_name)),
            "currency": metrics_data.currency,
            "period_type": PeriodType.UNKNOWN,
            "period": None,
            "value_type": FinancialValueType.ACTUAL,
            "source_citation_id": None,
        }
        for field_name, metric_type in _FLAT_FIELD_TO_METRIC_TYPE.items()
        if getattr(metrics_data, field_name) is not None
    ]


class FinancialAnalysisServiceError(Exception):
    """Base exception for financial analysis orchestration failures."""


class BusinessAnalysisRequiredError(FinancialAnalysisServiceError):
    """Raised when financial analysis is requested before the
    document's business analysis (`DocumentAnalysis`) has been run.

    Financial extraction reads the existing business analysis as
    context, so it cannot run until that analysis exists.
    """


class FinancialMetricsNotFoundError(FinancialAnalysisServiceError):
    """Raised when a document has not yet had financial analysis run."""


def _normalize_and_compute(
    result: FinancialExtractionResult,
) -> FinancialMetricsCreate:
    """Normalize raw AI extraction into a persistable, KPI-complete record.

    Fills in derivable values the AI did not provide directly
    (`arr`/`mrr` cross-derivation, `runway_months`), and computes a
    `confidence_score` reflecting how much of the extractable data the
    AI actually found. All derivation happens here, in the service
    layer, rather than by asking the AI to compute or estimate figures.

    Args:
        result: The validated raw financial extraction result.

    Returns:
        A `FinancialMetricsCreate` ready to persist.
    """
    arr = result.arr
    mrr = result.mrr
    if arr is None and mrr is not None:
        arr = mrr * 12
    elif mrr is None and arr is not None:
        mrr = arr / 12

    runway_months = None
    if result.cash is not None and result.burn_rate is not None and result.burn_rate > 0:
        runway_months = round(result.cash / result.burn_rate, 1)

    populated_count = sum(
        1
        for field_name in _EXTRACTABLE_FIELD_NAMES
        if getattr(result, field_name) is not None
    )
    confidence_score = round(populated_count / len(_EXTRACTABLE_FIELD_NAMES), 2)

    return FinancialMetricsCreate(
        currency=result.currency,
        revenue=result.revenue,
        arr=arr,
        mrr=mrr,
        gross_margin=result.gross_margin,
        ebitda=result.ebitda,
        burn_rate=result.burn_rate,
        runway_months=runway_months,
        cash=result.cash,
        customers=result.customers,
        growth_rate=result.growth_rate,
        cac=result.cac,
        ltv=result.ltv,
        valuation=result.valuation,
        confidence_score=confidence_score,
    )


def _build_extraction_input(text_content: str, analysis_summary: str | None) -> str:
    """Combine the document's business analysis summary and raw text.

    Providing the existing business-analysis summary as context helps
    the model correctly attribute figures (e.g. distinguishing company
    revenue from a mentioned competitor's revenue) without re-deriving
    facts already established by the business analysis.

    Args:
        text_content: The document's extracted plain text.
        analysis_summary: The document's business-analysis summary, or
            `None` if it has none.

    Returns:
        The combined text to send for financial extraction.
    """
    if not analysis_summary:
        return text_content

    return (
        f"Business context summary: {analysis_summary}\n\n"
        f"Full document text:\n{text_content}"
    )


class FinancialAnalysisService:
    """Use cases for triggering and retrieving document financial analysis."""

    @staticmethod
    async def analyze_financial_metrics(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> FinancialMetrics:
        """Extract and persist financial KPIs for a document.

        Requires that the document's business analysis
        (`DocumentAnalysis`) already exists, since it is read as context
        for the financial extraction. If the document already has a
        financial metrics record, it is overwritten in place, since each
        document has at most one.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the user requesting analysis.

        Returns:
            The newly created or updated `FinancialMetrics` record.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization.
            BusinessAnalysisRequiredError: If the document has not yet
                had its business analysis (`DocumentAnalysis`) run.
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured, or it is rejected as invalid (propagated
                from `AIService`).
            AIRequestFailedError: If the OpenAI request fails after
                retrying once (propagated from `AIService`).
            InvalidAIResponseError: If the AI's response is not valid
                JSON or does not match the expected schema (propagated
                from `AIService`).
        """
        document = await DocumentService.get_document(db, document_id, actor_id)

        try:
            analysis = await DocumentAnalysisService.get_analysis(
                db, document_id, actor_id
            )
        except AnalysisNotFoundError as exc:
            raise BusinessAnalysisRequiredError(
                "This document must be analyzed (POST /documents/{id}/analyze) "
                "before financial metrics can be extracted."
            ) from exc

        extraction_input = _build_extraction_input(
            document.text_content or "", analysis.summary
        )
        raw_result = await AIService.extract_financial_metrics(extraction_input)
        metrics_data = _normalize_and_compute(raw_result)

        existing = await _get_existing_metrics(db, document_id)

        if existing is not None:
            _apply_metrics_data(existing, metrics_data)
            metrics = existing
        else:
            metrics = FinancialMetrics(
                document_id=document_id, **metrics_data.model_dump()
            )
            db.add(metrics)

        await db.commit()
        await db.refresh(metrics)

        # Bug A fix: mirror the mappable fields into financial_facts too,
        # since Coverage/derived-metrics/validation read only that table.
        # See _facts_from_flat_metrics for exactly which fields and why.
        await FinancialFactsService.replace_facts_for_metrics(
            db,
            document_id,
            metrics=set(_FLAT_FIELD_TO_METRIC_TYPE.values()),
            facts=_facts_from_flat_metrics(metrics_data),
        )

        return metrics

    @staticmethod
    async def get_financial_metrics(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> FinancialMetrics:
        """Fetch a document's existing financial metrics.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.

        Returns:
            The document's `FinancialMetrics` record.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of its organization.
            FinancialMetricsNotFoundError: If the document has not yet
                had financial analysis run.
        """
        await DocumentService.get_document(db, document_id, actor_id)

        metrics = await _get_existing_metrics(db, document_id)
        if metrics is None:
            raise FinancialMetricsNotFoundError(
                "This document has not had financial analysis run yet."
            )

        return metrics

    @staticmethod
    async def extract_financial_facts(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
        ) -> list:
            """Extract and persist time-series financial facts with citations.

            This is a SEPARATE AI call from `analyze_financial_metrics`
            (which populates the flat, single-period `FinancialMetrics`
            row) — the two are not merged into one request, since asking
            the model for both a flat summary and a full time-series
            breakdown in one call degrades quality of both. Calling both
            this method and `analyze_financial_metrics` for the same
            document means two AI calls; this is a deliberate, disclosed
            cost, not an oversight.

            Args:
                db: The active database session.
                document_id: The document's id.
                actor_id: The id of the user requesting extraction.

            Returns:
                The newly persisted `FinancialFact` rows.

            Raises:
                DocumentNotFoundError: If the document does not exist, or
                    the actor is not a member of its organization.
                AIServiceNotConfiguredError, AIRequestFailedError,
                InvalidAIResponseError: Propagated from `AIService`.
            """
            document = await DocumentService.get_document(db, document_id, actor_id)

            cited = await AIService.generate_cited_financial_facts(document.text_content or "")

            fact_dicts = []
            for item in cited.facts:
                citation = await CitationService.create_citation(
                    db, document_id,
                    f"financial_facts.{item.metric.value}.{item.period or 'unknown'}",
                    item.quote, page_number=item.page_number, confidence=item.confidence,
                    extraction_version=EXTRACTION_VERSION,
                )
                fact_dicts.append({
                    "metric": item.metric, "value": item.value, "currency": item.currency,
                    "period_type": item.period_type, "period": item.period,
                    "value_type": item.value_type, "source_citation_id": citation.id,
                })

            return await FinancialFactsService.replace_facts(db, document_id, fact_dicts)


async def _get_existing_metrics(
    db: AsyncSession, document_id: uuid.UUID
) -> FinancialMetrics | None:
    """Fetch a document's financial metrics row, if one exists.

    Args:
        db: The active database session.
        document_id: The document's id.

    Returns:
        The `FinancialMetrics` if found, otherwise `None`.
    """
    result = await db.execute(
        select(FinancialMetrics).where(FinancialMetrics.document_id == document_id)
    )
    return result.scalar_one_or_none()


def _apply_metrics_data(
    metrics: FinancialMetrics, data: FinancialMetricsCreate
) -> None:
    """Overwrite an existing metrics row's fields with new data.

    Args:
        metrics: The existing `FinancialMetrics` to update in place.
        data: The new metrics data to apply.
    """
    for field, value in data.model_dump().items():
        setattr(metrics, field, value)