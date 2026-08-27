"""Deterministic consistency and anomaly detection for financial facts.

Every check here is a pure Python function over already-extracted
`FactPoint`s — never an LLM call. This mirrors the design of
`derived_metrics_service.py`: rules are independently unit-testable
against plain literals, with no database or AI dependency, and the
ORM-facing persistence (`persist_findings`) is a thin, separate layer.

Not every unusual value is an error — each rule assigns its own
severity (`info`/`warning`/`critical`) rather than treating every
finding as equally alarming.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.validation_finding import ValidationFinding
from app.schemas.validation import FindingSeverity, ValidationFindingResult
from app.services.derived_metrics_service import FactPoint, _yearly_actuals

_SEVERITY_ORDER = {FindingSeverity.CRITICAL: 0, FindingSeverity.WARNING: 1, FindingSeverity.INFO: 2}


def _latest(facts: list[FactPoint], metric) -> FactPoint | None:
    """Return the most recent year's fact for a metric, if any.

    Args:
        facts: The full set of facts.
        metric: The metric to look for.

    Returns:
        The `FactPoint` for the latest available year, or `None`.
    """
    years = _yearly_actuals(facts, metric)
    return years[-1][1] if years else None


# ---------------------------------------------------------------------------
# Individual rules — each is a pure function returning 0+ findings
# ---------------------------------------------------------------------------


def check_ebitda_exceeds_revenue(facts: list[FactPoint]) -> list[ValidationFindingResult]:
    """EBITDA should never exceed revenue for a real operating business."""
    ebitda = _latest(facts, M.EBITDA)
    revenue = _latest(facts, M.REVENUE)
    if not ebitda or not revenue or ebitda.period != revenue.period:
        return []
    if ebitda.value > revenue.value:
        return [
            ValidationFindingResult(
                severity=FindingSeverity.CRITICAL,
                category="financial_consistency",
                title="EBITDA exceeds revenue",
                description=(
                    f"The document reports EBITDA of {ebitda.value:,.0f} for "
                    f"{ebitda.period}, which exceeds reported revenue of "
                    f"{revenue.value:,.0f} for the same period. This is not "
                    f"possible for a normal operating business and suggests an "
                    f"extraction error or a genuine data inconsistency in the "
                    f"source document."
                ),
                affected_metrics=[M.EBITDA.value, M.REVENUE.value],
                suggested_question="Can you confirm the EBITDA and revenue figures for this period?",
            )
        ]
    return []


def check_ebitda_inconsistent_with_opex(facts: list[FactPoint]) -> list[ValidationFindingResult]:
    """EBITDA should roughly equal Revenue - Operating Expenses, within tolerance."""
    ebitda = _latest(facts, M.EBITDA)
    revenue = _latest(facts, M.REVENUE)
    opex = _latest(facts, M.OPERATING_EXPENSES)
    if not (ebitda and revenue and opex) or not (ebitda.period == revenue.period == opex.period):
        return []

    implied_ebitda = revenue.value - opex.value
    if revenue.value == 0:
        return []
    relative_gap = abs(implied_ebitda - ebitda.value) / abs(revenue.value)
    if relative_gap > 0.15:
        return [
            ValidationFindingResult(
                severity=FindingSeverity.WARNING,
                category="financial_consistency",
                title="EBITDA does not reconcile with revenue and operating expenses",
                description=(
                    f"Reported EBITDA for {ebitda.period} is {ebitda.value:,.0f}, but "
                    f"Revenue ({revenue.value:,.0f}) minus Operating Expenses "
                    f"({opex.value:,.0f}) implies {implied_ebitda:,.0f} — a gap of "
                    f"{relative_gap * 100:.0f}% of revenue. This may indicate "
                    f"non-operating items, a different EBITDA definition, or an "
                    f"extraction inconsistency."
                ),
                affected_metrics=[M.EBITDA.value, M.REVENUE.value, M.OPERATING_EXPENSES.value],
                suggested_question="What items reconcile reported EBITDA with revenue less operating expenses?",
            )
        ]
    return []


def check_negative_values_where_not_meaningful(facts: list[FactPoint]) -> list[ValidationFindingResult]:
    """Certain metrics (counts, valuations, revenue) should never be negative."""
    never_negative = {
        M.REVENUE, M.ARR, M.MRR, M.REGISTERED_CUSTOMERS, M.MONTHLY_ACTIVE_USERS, M.ORDERS,
        M.CASH, M.VALUATION_PRE_MONEY, M.VALUATION_POST_MONEY, M.FUNDING_AMOUNT,
    }
    findings = []
    for fact in facts:
        if fact.metric in never_negative and fact.value < 0:
            findings.append(
                ValidationFindingResult(
                    severity=FindingSeverity.CRITICAL,
                    category="financial_consistency",
                    title=f"Negative value for {fact.metric.value}",
                    description=(
                        f"{fact.metric.value} for {fact.period or 'an unspecified period'} "
                        f"is reported as {fact.value:,.0f}, which is negative. This metric "
                        f"is not meaningfully negative and likely indicates an extraction "
                        f"error."
                    ),
                    affected_metrics=[fact.metric.value],
                    suggested_question=None,
                )
            )
    return findings


def check_percentages_out_of_bounds(facts: list[FactPoint]) -> list[ValidationFindingResult]:
    """Percentage-like metrics (margins, churn, growth) outside plausible bounds."""
    percentage_metrics = {M.GROSS_MARGIN, M.CHURN_RATE, M.RETENTION_RATE}
    findings = []
    for fact in facts:
        if fact.metric in percentage_metrics and not (-1.0 <= fact.value <= 1.5):
            findings.append(
                ValidationFindingResult(
                    severity=FindingSeverity.WARNING,
                    category="data_quality",
                    title=f"{fact.metric.value} outside plausible range",
                    description=(
                        f"{fact.metric.value} for {fact.period or 'an unspecified period'} "
                        f"is {fact.value * 100:.1f}%, which is outside the plausible range "
                        f"for this metric. This may indicate the value was extracted as a "
                        f"raw number rather than a fraction, or is otherwise incorrect."
                    ),
                    affected_metrics=[fact.metric.value],
                    suggested_question=None,
                )
            )
    return findings


def check_registered_vs_active_confusion(facts: list[FactPoint]) -> list[ValidationFindingResult]:
    """Registered customers and monthly active users must not be conflated."""
    registered = _latest(facts, M.REGISTERED_CUSTOMERS)
    mau = _latest(facts, M.MONTHLY_ACTIVE_USERS)
    if not registered or not mau:
        return []

    if mau.value > registered.value:
        return [
            ValidationFindingResult(
                severity=FindingSeverity.WARNING,
                category="customer_metrics",
                title="Monthly active users exceeds registered customers",
                description=(
                    f"Monthly active users ({mau.value:,.0f}) exceeds registered "
                    f"customers ({registered.value:,.0f}). Active users should be a "
                    f"subset of registered users; this may indicate a mislabeled "
                    f"metric."
                ),
                affected_metrics=[M.REGISTERED_CUSTOMERS.value, M.MONTHLY_ACTIVE_USERS.value],
                suggested_question="Please confirm the definitions of registered customers versus monthly active users.",
            )
        ]

    activation_ratio = mau.value / registered.value if registered.value else 0
    if activation_ratio < 0.4:
        return [
            ValidationFindingResult(
                severity=FindingSeverity.WARNING,
                category="customer_metrics",
                title="Customer metric may be misleading",
                description=(
                    f"The document reports {registered.value:,.0f} registered "
                    f"customers but only {mau.value:,.0f} monthly active users "
                    f"({activation_ratio * 100:.0f}% activation). Scale claims based "
                    f"on the registered-customer figure alone would overstate actual "
                    f"engagement."
                ),
                affected_metrics=[M.REGISTERED_CUSTOMERS.value, M.MONTHLY_ACTIVE_USERS.value],
                suggested_question="What percentage of registered users placed an order in the last 90 days?",
            )
        ]
    return []


def check_ltv_cac_reported_vs_calculated(facts: list[FactPoint], reported_ratio: float | None) -> list[ValidationFindingResult]:
    """Compare a source-reported LTV/CAC ratio against the calculated one.

    Args:
        facts: The full set of facts.
        reported_ratio: The LTV/CAC ratio as explicitly stated in the
            source document (e.g. "improved from 5.1x to 8.1x" ->
            8.1), or `None` if the source did not state one directly.
    """
    if reported_ratio is None:
        return []
    ltv = _latest(facts, M.LTV)
    cac = _latest(facts, M.CAC)
    if not ltv or not cac or cac.value == 0:
        return []

    calculated_ratio = ltv.value / cac.value
    if abs(calculated_ratio - reported_ratio) / reported_ratio > 0.1:
        return [
            ValidationFindingResult(
                severity=FindingSeverity.WARNING,
                category="unit_economics",
                title="Reported LTV/CAC does not match calculated value",
                description=(
                    f"The source document states an LTV/CAC ratio of "
                    f"{reported_ratio:.1f}x, but calculating LTV ({ltv.value:,.0f}) "
                    f"divided by CAC ({cac.value:,.0f}) gives {calculated_ratio:.1f}x."
                ),
                affected_metrics=[M.LTV.value, M.CAC.value],
                suggested_question="What methodology was used to calculate the reported LTV/CAC ratio?",
            )
        ]
    return []


def check_growth_claims_without_time_series(
    facts: list[FactPoint], claimed_growth_metrics: list[str]
) -> list[ValidationFindingResult]:
    """Flag growth claims made in narrative text with no supporting time-series data.

    Args:
        facts: The full set of facts.
        claimed_growth_metrics: Metric names (as strings) the source
            document narratively claims are growing, without
            necessarily providing multi-period figures for them.
    """
    findings = []
    for metric_name in claimed_growth_metrics:
        try:
            metric = M(metric_name)
        except ValueError:
            continue
        years = _yearly_actuals(facts, metric)
        if len(years) < 2:
            findings.append(
                ValidationFindingResult(
                    severity=FindingSeverity.INFO,
                    category="data_quality",
                    title=f"Growth claimed for {metric_name} without supporting time series",
                    description=(
                        f"The document narratively describes growth in {metric_name}, "
                        f"but fewer than two periods of actual data are available to "
                        f"verify the claim."
                    ),
                    affected_metrics=[metric_name],
                    suggested_question=f"Can you provide historical {metric_name} figures by period?",
                )
            )
    return findings


def check_profitable_claim_without_net_income(
    facts: list[FactPoint], claims_profitability: bool
) -> list[ValidationFindingResult]:
    """Flag a 'profitable' claim when only EBITDA is positive and net income is absent/negative.

    Args:
        facts: The full set of facts.
        claims_profitability: Whether the source document narratively
            claims the company is profitable.
    """
    if not claims_profitability:
        return []
    ebitda = _latest(facts, M.EBITDA)
    net_income = _latest(facts, M.NET_INCOME)

    if ebitda and ebitda.value > 0 and (not net_income or net_income.value <= 0):
        return [
            ValidationFindingResult(
                severity=FindingSeverity.WARNING,
                category="financial_consistency",
                title="\"Profitable\" claim not supported by net income",
                description=(
                    "The document describes the company as profitable, and EBITDA is "
                    f"positive ({ebitda.value:,.0f}), but net income is "
                    + (f"negative ({net_income.value:,.0f})" if net_income else "not reported")
                    + ". EBITDA-positive is not the same as net-income-positive."
                ),
                affected_metrics=[M.EBITDA.value, M.NET_INCOME.value],
                suggested_question="What is net income after accounting for depreciation, interest, and taxes?",
            )
        ]
    return []


def check_runway_without_inputs(facts: list[FactPoint], runway_claimed: bool) -> list[ValidationFindingResult]:
    """Flag a runway figure or claim when cash and burn rate are not both available.

    Args:
        facts: The full set of facts.
        runway_claimed: Whether the source document states a runway
            figure without necessarily providing both cash and burn.
    """
    if not runway_claimed:
        return []
    cash = next((f for f in facts if f.metric == M.CASH), None)
    burn = next((f for f in facts if f.metric == M.BURN_RATE), None)
    if not cash or not burn:
        missing = "cash" if not cash else "burn rate"
        return [
            ValidationFindingResult(
                severity=FindingSeverity.WARNING,
                category="financial_consistency",
                title="Runway claim lacks supporting inputs",
                description=(
                    f"A runway figure is referenced in the document, but {missing} is "
                    f"not available to independently verify it."
                ),
                affected_metrics=[M.CASH.value, M.BURN_RATE.value],
                suggested_question=f"What is the current monthly {missing}?",
            )
        ]
    return []


def check_valuation_or_funding_mislabeled_as_revenue(facts: list[FactPoint]) -> list[ValidationFindingResult]:
    """Flag when a valuation or funding figure coincides exactly with a reported revenue figure."""
    revenue_values = {round(f.value, 2) for f in facts if f.metric == M.REVENUE}
    findings = []
    for fact in facts:
        if fact.metric in (M.VALUATION_POST_MONEY, M.VALUATION_PRE_MONEY, M.FUNDING_AMOUNT):
            if round(fact.value, 2) in revenue_values:
                findings.append(
                    ValidationFindingResult(
                        severity=FindingSeverity.CRITICAL,
                        category="extraction_quality",
                        title=f"{fact.metric.value} value matches a reported revenue figure",
                        description=(
                            f"{fact.metric.value} of {fact.value:,.0f} exactly matches a "
                            f"revenue figure recorded for this document. This strongly "
                            f"suggests one of the two was mis-extracted."
                        ),
                        affected_metrics=[fact.metric.value, M.REVENUE.value],
                        suggested_question=None,
                    )
                )
    return findings


def check_forecast_presented_as_actual(facts: list[FactPoint], future_year: int) -> list[ValidationFindingResult]:
    """Flag any fact for a future year that is typed as ACTUAL rather than FORECAST.

    Args:
        facts: The full set of facts.
        future_year: The first year that should be considered "future"
            relative to the document's as-of date (e.g. if the document
            is dated 2025, `future_year=2026`).
    """
    findings = []
    for fact in facts:
        if (
            fact.period_type.value == "year"
            and fact.period
            and fact.period.isdigit()
            and int(fact.period) >= future_year
            and fact.value_type.value == "actual"
        ):
            findings.append(
                ValidationFindingResult(
                    severity=FindingSeverity.WARNING,
                    category="data_quality",
                    title=f"Future-year {fact.metric.value} labeled as actual",
                    description=(
                        f"{fact.metric.value} for {fact.period} is marked as an actual "
                        f"historical value, but {fact.period} has not yet occurred as of "
                        f"this document's context. It should likely be a forecast or "
                        f"target."
                    ),
                    affected_metrics=[fact.metric.value],
                    suggested_question=None,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Registry + entry point
# ---------------------------------------------------------------------------

# Rules that need only `facts` are run unconditionally. Rules needing
# document-analysis context (narrative claims, reported ratios, an
# as-of date) are run separately by the caller, which has that context —
# keeping this registry usable standalone in tests.
_UNCONDITIONAL_RULES = [
    check_ebitda_exceeds_revenue,
    check_ebitda_inconsistent_with_opex,
    check_negative_values_where_not_meaningful,
    check_percentages_out_of_bounds,
    check_registered_vs_active_confusion,
    check_valuation_or_funding_mislabeled_as_revenue,
]


def run_all_validations(facts: list[FactPoint]) -> list[ValidationFindingResult]:
    """Run every unconditional validation rule against a set of facts.

    Rules requiring additional narrative context (LTV/CAC as explicitly
    reported, profitability claims, runway claims, growth claims, an
    as-of date for forecast detection) are not included here — call
    them individually when that context is available (typically
    alongside a `DocumentAnalysis` row).

    Args:
        facts: The full set of financial facts for a document.

    Returns:
        All findings from all unconditional rules, sorted with
        `CRITICAL` first, then `WARNING`, then `INFO`.
    """
    findings: list[ValidationFindingResult] = []
    for rule in _UNCONDITIONAL_RULES:
        findings.extend(rule(facts))
    return sorted(findings, key=lambda f: _SEVERITY_ORDER[f.severity])


class ValidationService:
    """Persists and retrieves validation findings, replacing any prior results."""

    @staticmethod
    async def list_findings(db: AsyncSession, document_id: uuid.UUID) -> list[ValidationFinding]:
        """Fetch a document's persisted validation findings.

        Minimal read accessor added for `findings_service.py` (Evidence
        Layer plan, Step 5), which wraps these rows into the unified
        `Finding` shape — the rule engine and `persist_findings` above
        are unchanged.

        Args:
            db: The active database session.
            document_id: The document's id.

        Returns:
            All `ValidationFinding` rows for the document, unordered.
        """
        result = await db.execute(
            select(ValidationFinding).where(ValidationFinding.document_id == document_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def persist_findings(
        db: AsyncSession, document_id: uuid.UUID, findings: list[ValidationFindingResult]
    ) -> list[ValidationFinding]:
        """Replace a document's validation findings with a new set.

        Args:
            db: The active database session.
            document_id: The document these findings belong to.
            findings: The findings to persist.

        Returns:
            The newly persisted `ValidationFinding` rows.
        """
        await db.execute(delete(ValidationFinding).where(ValidationFinding.document_id == document_id))

        rows = [
            ValidationFinding(
                document_id=document_id,
                severity=f.severity.value,
                category=f.category,
                title=f.title,
                description=f.description,
                affected_metrics=f.affected_metrics,
                sources=[],
                suggested_question=f.suggested_question,
            )
            for f in findings
        ]
        db.add_all(rows)
        await db.commit()
        for row in rows:
            await db.refresh(row)
        return rows