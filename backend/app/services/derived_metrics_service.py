"""Deterministic derived-metrics calculation engine.

Computes growth, profitability, unit-economics, and valuation metrics
from raw financial facts using fixed Python formulas — never an LLM
call. Every function here is pure: given the same `FactPoint` list, it
always returns the same result, with no I/O, no randomness, and no
network access. This is deliberate: these are the numbers an investor
will use to make a decision, and they must be independently auditable
and reproducible, not subject to model variance.

`FactPoint` is a lightweight, DB-independent representation of a single
financial fact. Keeping calculators decoupled from the ORM
(`FinancialFact`) means the entire engine can be unit-tested with plain
Python literals — no database, no fixtures, no async setup — and the
ORM-facing conversion lives in one small function
(`facts_from_financial_facts`) at the bottom of this module.
"""

from dataclasses import dataclass

from app.models.financial_fact import FinancialMetricType, FinancialValueType, PeriodType
from app.schemas.derived_metrics import DerivedMetricResult, MetricInputRef, MetricStatus

M = FinancialMetricType
V = FinancialValueType
P = PeriodType


@dataclass(frozen=True)
class FactPoint:
    """A single financial fact, decoupled from the database.

    Attributes:
        metric: Which financial/operating metric this is.
        value: The numeric value.
        period: The period string (e.g. `"2025"`), or `None`.
        period_type: The granularity of `period`.
        value_type: Whether this is actual/forecast/target/estimate/derived.
        currency: The ISO 4217 currency code, or `None`.
        source_citation_id: The supporting citation's id, or `None`.
    """

    metric: FinancialMetricType
    value: float
    period: str | None
    period_type: PeriodType
    value_type: FinancialValueType
    currency: str | None = None
    source_citation_id: str | None = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _yearly_actuals(facts: list[FactPoint], metric: FinancialMetricType) -> list[tuple[int, FactPoint]]:
    """Return a metric's actual-or-estimated, year-period facts, sorted by year.

    Includes both ACTUAL and ESTIMATE value types, since many real-world
    figures used in calculations (e.g. LTV) are explicitly stated as
    estimates by the source document rather than hard actuals, and
    excluding them entirely would make otherwise-calculable metrics
    (like LTV/CAC) incorrectly report MISSING_INPUTS. FORECAST and
    TARGET are still excluded — those represent different periods'
    projections, not this period's estimated reality, and mixing them
    into historical calculations would misrepresent the result (see
    test_forecast_values_excluded_from_actual_growth).

    Args:
        facts: The full set of facts to search.
        metric: The metric to filter for.

    Returns:
        A list of `(year, FactPoint)` tuples, sorted ascending by year.
    """
    candidates = [
        f
        for f in facts
        if f.metric == metric
        and f.period_type == P.YEAR
        and f.value_type in (V.ACTUAL, V.ESTIMATE)
        and f.period is not None
        and f.period.isdigit()
    ]
    return sorted(((int(f.period), f) for f in candidates), key=lambda pair: pair[0])


def _fact_at(
    facts: list[FactPoint],
    metric: FinancialMetricType,
    period: str,
    period_type: PeriodType = P.YEAR,
) -> FactPoint | None:
    """Return the single fact for a metric at an exact period, if any.

    If more than one fact matches (e.g. both an ACTUAL and an ESTIMATE
    for the same metric/period), the first `ACTUAL` match is preferred;
    if none is `ACTUAL`, the first match of any value type is returned.
    This is a deliberate, simple tie-break rather than raising —
    genuine ambiguity detection belongs to the validation service
    (a later step), not silently inside every calculator.

    Args:
        facts: The full set of facts to search.
        metric: The metric to look for.
        period: The exact period string to match.
        period_type: The period granularity to match.

    Returns:
        The matching `FactPoint`, or `None` if no fact matches.
    """
    matches = [
        f for f in facts if f.metric == metric and f.period == period and f.period_type == period_type
    ]
    if not matches:
        return None
    actual_matches = [f for f in matches if f.value_type == V.ACTUAL]
    return actual_matches[0] if actual_matches else matches[0]


def _input_ref(name: str, fact: FactPoint) -> MetricInputRef:
    """Build a `MetricInputRef` from a `FactPoint`.

    Args:
        name: The human-readable label for this input.
        fact: The source fact.

    Returns:
        The corresponding `MetricInputRef`.
    """
    return MetricInputRef(
        name=name,
        value=fact.value,
        period=fact.period,
        source_citation_id=fact.source_citation_id,
    )


def _confidence_for(*inputs: FactPoint) -> float:
    """Compute a confidence score from the value types of the inputs used.

    Args:
        *inputs: The facts used in a calculation.

    Returns:
        `1.0` if every input is `ACTUAL`; `0.75` if any input is an
        `ESTIMATE`; `0.6` if any input is `FORECAST` or `TARGET` (a
        weaker basis for a "calculated" figure, but still explicitly
        labeled rather than silently treated as actual).
    """
    value_types = {f.value_type for f in inputs}
    if value_types <= {V.ACTUAL, V.DERIVED}:
        return 1.0
    if V.ESTIMATE in value_types:
        return 0.75
    return 0.6


def _missing_result(metric: str, formula: str, period: str | None, missing: list[str]) -> DerivedMetricResult:
    """Build a `MISSING_INPUTS` result.

    Args:
        metric: The metric identifier.
        formula: The formula description.
        period: The period this result would apply to, or `None`.
        missing: The names of the facts that could not be found.

    Returns:
        A `DerivedMetricResult` with `status=MISSING_INPUTS`.
    """
    return DerivedMetricResult(
        metric=metric,
        period=period,
        value=None,
        display_value=None,
        formula=formula,
        inputs=[],
        status=MetricStatus.MISSING_INPUTS,
        confidence=None,
        notes=f"Missing required input(s): {', '.join(missing)}.",
    )


def _fmt_percent(value: float) -> str:
    """Format a fraction as a percentage string (e.g. `0.417` -> `"41.7%"`)."""
    return f"{value * 100:.1f}%"


def _fmt_ratio(value: float) -> str:
    """Format a ratio as an `"Nx"` string (e.g. `8.0952` -> `"8.1x"`)."""
    return f"{value:.1f}x"


def _fmt_currency(value: float, currency: str | None) -> str:
    """Format a currency value with M/K suffixes (e.g. `27_840_000` -> `"$27.8M"`)."""
    symbol = "$" if (currency or "USD") == "USD" else f"{currency} "
    magnitude = abs(value)
    sign = "-" if value < 0 else ""
    if magnitude >= 1_000_000:
        return f"{sign}{symbol}{magnitude / 1_000_000:.1f}M"
    if magnitude >= 1_000:
        return f"{sign}{symbol}{magnitude / 1_000:.1f}K"
    return f"{sign}{symbol}{magnitude:.2f}"


def _fmt_number(value: float) -> str:
    """Format a plain count (e.g. `2_800_000` -> `"2,800,000"`)."""
    return f"{value:,.0f}"


# ---------------------------------------------------------------------------
# Growth metrics
# ---------------------------------------------------------------------------

_GROWTH_METRIC_LABELS: dict[FinancialMetricType, str] = {
    M.REVENUE: "Revenue",
    M.ORDERS: "Orders",
    M.REGISTERED_CUSTOMERS: "Registered Customers",
    M.MONTHLY_ACTIVE_USERS: "Monthly Active Users",
    M.AOV: "Average Order Value",
}


def _yoy_growth_series(facts: list[FactPoint], metric: FinancialMetricType) -> list[DerivedMetricResult]:
    """Compute year-over-year growth for every consecutive year pair available.

    Args:
        facts: The full set of facts.
        metric: The metric to compute growth for.

    Returns:
        One `DerivedMetricResult` per consecutive year pair found (e.g.
        2023->2024, 2024->2025). Returns a single `MISSING_INPUTS`
        result if fewer than two years of actual data exist.
    """
    label = _GROWTH_METRIC_LABELS.get(metric, metric.value)
    result_key = f"{metric.value}_yoy_growth"
    formula = f"({label}[t] - {label}[t-1]) / {label}[t-1]"

    years = _yearly_actuals(facts, metric)
    if len(years) < 2:
        return [_missing_result(result_key, formula, None, [f"{label} for at least two consecutive years"])]

    results: list[DerivedMetricResult] = []
    for (prev_year, prev_fact), (curr_year, curr_fact) in zip(years, years[1:]):
        if curr_year != prev_year + 1:
            results.append(
                DerivedMetricResult(
                    metric=result_key,
                    period=str(curr_year),
                    value=None,
                    display_value=None,
                    formula=formula,
                    inputs=[],
                    status=MetricStatus.PERIOD_MISMATCH,
                    confidence=None,
                    notes=f"{label} for {prev_year} and {curr_year} are not consecutive years.",
                )
            )
            continue

        if prev_fact.value == 0:
            results.append(
                DerivedMetricResult(
                    metric=result_key,
                    period=str(curr_year),
                    value=None,
                    display_value=None,
                    formula=formula,
                    inputs=[_input_ref(f"{label} ({prev_year})", prev_fact), _input_ref(f"{label} ({curr_year})", curr_fact)],
                    status=MetricStatus.INVALID,
                    confidence=None,
                    notes=f"{label} for {prev_year} is zero; growth rate is undefined.",
                )
            )
            continue

        growth = (curr_fact.value - prev_fact.value) / prev_fact.value
        results.append(
            DerivedMetricResult(
                metric=result_key,
                period=str(curr_year),
                value=growth,
                display_value=_fmt_percent(growth),
                formula=formula,
                inputs=[_input_ref(f"{label} ({prev_year})", prev_fact), _input_ref(f"{label} ({curr_year})", curr_fact)],
                status=MetricStatus.CALCULATED,
                confidence=_confidence_for(prev_fact, curr_fact),
            )
        )
    return results


def _cagr(facts: list[FactPoint], metric: FinancialMetricType) -> DerivedMetricResult:
    """Compute the compound annual growth rate across the full available range.

    Args:
        facts: The full set of facts.
        metric: The metric to compute CAGR for.

    Returns:
        A single `DerivedMetricResult` covering the earliest-to-latest
        year range, or `MISSING_INPUTS` if fewer than two years exist.
    """
    label = _GROWTH_METRIC_LABELS.get(metric, metric.value)
    result_key = f"{metric.value}_cagr"
    formula = f"({label}[end] / {label}[start]) ^ (1 / years) - 1"

    years = _yearly_actuals(facts, metric)
    if len(years) < 2:
        return _missing_result(result_key, formula, None, [f"{label} for at least two years"])

    (start_year, start_fact), (end_year, end_fact) = years[0], years[-1]
    num_years = end_year - start_year
    period_label = f"{start_year}-{end_year}"

    if num_years <= 0 or start_fact.value <= 0:
        return DerivedMetricResult(
            metric=result_key,
            period=period_label,
            value=None,
            display_value=None,
            formula=formula,
            inputs=[_input_ref(f"{label} ({start_year})", start_fact), _input_ref(f"{label} ({end_year})", end_fact)],
            status=MetricStatus.INVALID,
            confidence=None,
            notes="CAGR requires a positive starting value and a positive year span.",
        )

    cagr_value = (end_fact.value / start_fact.value) ** (1 / num_years) - 1
    return DerivedMetricResult(
        metric=result_key,
        period=period_label,
        value=cagr_value,
        display_value=_fmt_percent(cagr_value),
        formula=formula,
        inputs=[_input_ref(f"{label} ({start_year})", start_fact), _input_ref(f"{label} ({end_year})", end_fact)],
        status=MetricStatus.CALCULATED,
        confidence=_confidence_for(start_fact, end_fact),
    )


def _growth_trend(revenue_yoy_results: list[DerivedMetricResult]) -> DerivedMetricResult:
    """Classify whether revenue growth is accelerating, decelerating, or stable.

    Args:
        revenue_yoy_results: The output of `_yoy_growth_series` for
            revenue, in chronological order.

    Returns:
        A `DerivedMetricResult` with `display_value` in
        `{"accelerating", "decelerating", "stable"}`, or
        `MISSING_INPUTS` if fewer than two calculated growth rates
        are available to compare.
    """
    formula = "Comparison of consecutive YoY growth rates"
    calculated = [r for r in revenue_yoy_results if r.status == MetricStatus.CALCULATED and r.value is not None]

    if len(calculated) < 2:
        return _missing_result(
            "revenue_growth_trend", formula, None, ["at least two calculated YoY growth rates"]
        )

    rates = [r.value for r in calculated]
    if all(later < earlier for earlier, later in zip(rates, rates[1:])):
        trend = "decelerating"
    elif all(later > earlier for earlier, later in zip(rates, rates[1:])):
        trend = "accelerating"
    else:
        trend = "mixed"

    periods = [r.period for r in calculated]
    return DerivedMetricResult(
        metric="revenue_growth_trend",
        period=f"{periods[0]}-{periods[-1]}",
        value=None,
        display_value=trend,
        formula=formula,
        inputs=[
            MetricInputRef(name=f"YoY growth ({r.period})", value=r.value, period=r.period)
            for r in calculated
        ],
        status=MetricStatus.CALCULATED,
        confidence=1.0,
        notes=(
            "Growth remains positive but the rate of growth is declining year over year."
            if trend == "decelerating"
            else None
        ),
    )


def calculate_growth_metrics(facts: list[FactPoint]) -> list[DerivedMetricResult]:
    """Compute all growth metrics: YoY, CAGR, and trend classification.

    Args:
        facts: The full set of financial facts for a document.

    Returns:
        A flat list of `DerivedMetricResult`s covering revenue YoY,
        revenue CAGR, revenue growth trend, and YoY growth for orders,
        registered customers, MAU, and AOV where data exists.
    """
    results: list[DerivedMetricResult] = []

    revenue_yoy = _yoy_growth_series(facts, M.REVENUE)
    results.extend(revenue_yoy)
    results.append(_cagr(facts, M.REVENUE))
    results.append(_growth_trend(revenue_yoy))

    for metric in (M.ORDERS, M.REGISTERED_CUSTOMERS, M.MONTHLY_ACTIVE_USERS, M.AOV):
        results.extend(_yoy_growth_series(facts, metric))

    return results


# ---------------------------------------------------------------------------
# Profitability metrics
# ---------------------------------------------------------------------------


def _margin_series(
    facts: list[FactPoint], numerator_metric: FinancialMetricType, result_key: str, label: str
) -> list[DerivedMetricResult]:
    """Compute `numerator / revenue` for every period both are available.

    Args:
        facts: The full set of facts.
        numerator_metric: The metric to divide by revenue.
        result_key: The output metric identifier.
        label: The human-readable name for the numerator.

    Returns:
        One result per period with both facts present, or a single
        `MISSING_INPUTS` result if no period has both.
    """
    formula = f"{label} / Revenue"
    numerator_years = {year: fact for year, fact in _yearly_actuals(facts, numerator_metric)}
    revenue_years = {year: fact for year, fact in _yearly_actuals(facts, M.REVENUE)}
    common_years = sorted(set(numerator_years) & set(revenue_years))

    if not common_years:
        return [_missing_result(result_key, formula, None, [label, "Revenue (same period)"])]

    results = []
    for year in common_years:
        numerator_fact = numerator_years[year]
        revenue_fact = revenue_years[year]
        if revenue_fact.value == 0:
            results.append(
                DerivedMetricResult(
                    metric=result_key,
                    period=str(year),
                    value=None,
                    display_value=None,
                    formula=formula,
                    inputs=[_input_ref(label, numerator_fact), _input_ref("Revenue", revenue_fact)],
                    status=MetricStatus.INVALID,
                    confidence=None,
                    notes=f"Revenue for {year} is zero; margin is undefined.",
                )
            )
            continue

        margin = numerator_fact.value / revenue_fact.value
        results.append(
            DerivedMetricResult(
                metric=result_key,
                period=str(year),
                value=margin,
                display_value=_fmt_percent(margin),
                formula=formula,
                inputs=[_input_ref(label, numerator_fact), _input_ref("Revenue", revenue_fact)],
                status=MetricStatus.CALCULATED,
                confidence=_confidence_for(numerator_fact, revenue_fact),
            )
        )
    return results


def _change_series(
    facts: list[FactPoint], metric: FinancialMetricType, result_key: str, label: str, as_percent_points: bool = False
) -> DerivedMetricResult:
    """Compute the change in a metric between its earliest and latest year.

    Args:
        facts: The full set of facts.
        metric: The metric to compute a change for.
        result_key: The output metric identifier.
        label: The human-readable name for this metric.
        as_percent_points: If `True`, format the change as percentage
            points (e.g. `"+7.0pp"`) rather than a currency delta —
            used for margin-type metrics already expressed as
            fractions.

    Returns:
        A single `DerivedMetricResult` covering the full available
        range, or `MISSING_INPUTS` if fewer than two years exist.
    """
    formula = f"{label}[end] - {label}[start]"
    years = _yearly_actuals(facts, metric)

    if len(years) < 2:
        return _missing_result(result_key, formula, None, [f"{label} for at least two years"])

    (start_year, start_fact), (end_year, end_fact) = years[0], years[-1]
    delta = end_fact.value - start_fact.value
    period_label = f"{start_year}-{end_year}"

    display = f"{'+' if delta >= 0 else ''}{delta * 100:.1f}pp" if as_percent_points else (
        f"{'+' if delta >= 0 else ''}{_fmt_currency(delta, end_fact.currency)}"
    )

    notes = None
    if metric == M.EBITDA and start_fact.value < 0 <= end_fact.value:
        notes = "The business transitioned from negative to positive EBITDA."

    return DerivedMetricResult(
        metric=result_key,
        period=period_label,
        value=delta,
        display_value=display,
        formula=formula,
        inputs=[_input_ref(f"{label} ({start_year})", start_fact), _input_ref(f"{label} ({end_year})", end_fact)],
        status=MetricStatus.CALCULATED,
        confidence=_confidence_for(start_fact, end_fact),
        notes=notes,
    )


def _gross_profit_estimate_series(facts: list[FactPoint]) -> list[DerivedMetricResult]:
    """Estimate gross profit as `Revenue x Gross Margin` for each shared period.

    Only computed when a direct `GROSS_PROFIT` fact is not already
    present for that period — if the source document states gross
    profit directly, that figure should be used as a reported fact
    instead of this derived estimate (handled by the caller, not this
    function, which always computes the estimate when its inputs
    exist).

    Args:
        facts: The full set of facts.

    Returns:
        One result per period with both revenue and gross margin
        available, or a single `MISSING_INPUTS` result otherwise.
    """
    formula = "Revenue x Gross Margin"
    margin_years = {year: fact for year, fact in _yearly_actuals(facts, M.GROSS_MARGIN)}
    revenue_years = {year: fact for year, fact in _yearly_actuals(facts, M.REVENUE)}
    common_years = sorted(set(margin_years) & set(revenue_years))

    if not common_years:
        return [_missing_result("gross_profit_estimate", formula, None, ["Gross Margin", "Revenue (same period)"])]

    results = []
    for year in common_years:
        margin_fact = margin_years[year]
        revenue_fact = revenue_years[year]
        estimate = revenue_fact.value * margin_fact.value
        results.append(
            DerivedMetricResult(
                metric="gross_profit_estimate",
                period=str(year),
                value=estimate,
                display_value=_fmt_currency(estimate, revenue_fact.currency),
                formula=formula,
                inputs=[_input_ref("Revenue", revenue_fact), _input_ref("Gross Margin", margin_fact)],
                status=MetricStatus.CALCULATED,
                confidence=_confidence_for(revenue_fact, margin_fact),
                notes="Estimated; the source document did not report gross profit directly.",
            )
        )
    return results


def calculate_profitability_metrics(facts: list[FactPoint]) -> list[DerivedMetricResult]:
    """Compute all profitability metrics.

    Args:
        facts: The full set of financial facts for a document.

    Returns:
        A flat list covering EBITDA margin, net margin, opex ratio,
        gross profit estimate, change in gross margin, and change in
        EBITDA (including a transition-to-profitability note when
        applicable).
    """
    results: list[DerivedMetricResult] = []
    results.extend(_margin_series(facts, M.EBITDA, "ebitda_margin", "EBITDA"))
    results.extend(_margin_series(facts, M.NET_INCOME, "net_margin", "Net Income"))
    results.extend(_margin_series(facts, M.OPERATING_EXPENSES, "operating_expense_ratio", "Operating Expenses"))
    results.extend(_gross_profit_estimate_series(facts))
    results.append(_change_series(facts, M.GROSS_MARGIN, "gross_margin_change", "Gross Margin", as_percent_points=True))
    results.append(_change_series(facts, M.EBITDA, "ebitda_change", "EBITDA"))
    return results


# ---------------------------------------------------------------------------
# Unit economics metrics
# ---------------------------------------------------------------------------


def _ratio_series(
    facts: list[FactPoint],
    numerator_metric: FinancialMetricType,
    denominator_metric: FinancialMetricType,
    result_key: str,
    numerator_label: str,
    denominator_label: str,
    display: str = "ratio",
) -> list[DerivedMetricResult]:
    """Compute `numerator / denominator` for every period both share.

    Args:
        facts: The full set of facts.
        numerator_metric: The metric for the numerator.
        denominator_metric: The metric for the denominator.
        result_key: The output metric identifier.
        numerator_label: Human-readable numerator name.
        denominator_label: Human-readable denominator name.
        display: `"ratio"` for an `"Nx"` format, `"currency"` for a
            dollar-formatted result.

    Returns:
        One result per shared period, or a single `MISSING_INPUTS`
        result if no period has both facts.
    """
    formula = f"{numerator_label} / {denominator_label}"
    num_years = {year: fact for year, fact in _yearly_actuals(facts, numerator_metric)}
    den_years = {year: fact for year, fact in _yearly_actuals(facts, denominator_metric)}
    common_years = sorted(set(num_years) & set(den_years))

    if not common_years:
        return [_missing_result(result_key, formula, None, [numerator_label, f"{denominator_label} (same period)"])]

    results = []
    for year in common_years:
        num_fact = num_years[year]
        den_fact = den_years[year]
        if den_fact.value == 0:
            results.append(
                DerivedMetricResult(
                    metric=result_key,
                    period=str(year),
                    value=None,
                    display_value=None,
                    formula=formula,
                    inputs=[_input_ref(numerator_label, num_fact), _input_ref(denominator_label, den_fact)],
                    status=MetricStatus.INVALID,
                    confidence=None,
                    notes=f"{denominator_label} for {year} is zero.",
                )
            )
            continue

        ratio = num_fact.value / den_fact.value
        display_value = _fmt_ratio(ratio) if display == "ratio" else _fmt_currency(ratio, num_fact.currency)
        results.append(
            DerivedMetricResult(
                metric=result_key,
                period=str(year),
                value=ratio,
                display_value=display_value,
                formula=formula,
                inputs=[_input_ref(numerator_label, num_fact), _input_ref(denominator_label, den_fact)],
                status=MetricStatus.CALCULATED,
                confidence=_confidence_for(num_fact, den_fact),
            )
        )
    return results


def _orders_per_active_user(facts: list[FactPoint]) -> DerivedMetricResult:
    """Compute orders per active user, only when periods are truly compatible.

    `MONTHLY_ACTIVE_USERS` is inherently a monthly figure while
    `ORDERS` in this schema is typically reported annually — dividing
    an annual count by a single month's active-user snapshot would
    silently overstate orders-per-user by roughly 12x. Rather than
    guess at an annualization factor, this returns `PERIOD_MISMATCH`
    whenever both facts are present, explaining exactly why the
    calculation is being withheld — this is a deliberate,
    spec-mandated safeguard, not a bug.

    Args:
        facts: The full set of facts.

    Returns:
        A `PERIOD_MISMATCH` result if both facts exist, or
        `MISSING_INPUTS` if either is absent.
    """
    formula = "Orders / Monthly Active Users"
    orders_years = _yearly_actuals(facts, M.ORDERS)
    mau_years = _yearly_actuals(facts, M.MONTHLY_ACTIVE_USERS)

    if not orders_years or not mau_years:
        missing = []
        if not orders_years:
            missing.append("Orders")
        if not mau_years:
            missing.append("Monthly Active Users")
        return _missing_result("orders_per_active_user", formula, None, missing)

    return DerivedMetricResult(
        metric="orders_per_active_user",
        period=None,
        value=None,
        display_value=None,
        formula=formula,
        inputs=[],
        status=MetricStatus.PERIOD_MISMATCH,
        confidence=None,
        notes=(
            "Orders are reported as an annual total while Monthly Active Users is a "
            "point-in-time monthly snapshot; dividing one by the other without an "
            "explicit annualization basis would misrepresent order frequency per user."
        ),
    )


def _cac_payback(facts: list[FactPoint]) -> DerivedMetricResult:
    """Attempt CAC payback period; withholds the result if inputs are insufficient.

    CAC payback requires monthly gross margin per customer, which this
    document schema does not directly provide. Rather than approximate
    it from unrelated figures, this always returns `MISSING_INPUTS`
    until a genuine per-customer monthly margin fact is available.

    Args:
        facts: The full set of facts.

    Returns:
        A `MISSING_INPUTS` result explaining exactly what's needed.
    """
    return _missing_result(
        "cac_payback_months",
        "CAC / (Monthly Revenue per Customer x Gross Margin)",
        None,
        ["monthly revenue per customer", "gross margin applicable to that revenue"],
    )


def calculate_unit_economics_metrics(facts: list[FactPoint]) -> list[DerivedMetricResult]:
    """Compute all unit-economics metrics.

    Args:
        facts: The full set of financial facts for a document.

    Returns:
        A flat list covering LTV/CAC, revenue per registered customer,
        revenue per MAU (kept strictly distinct from registered
        customers, never combined), revenue per order, orders per
        active user (a deliberate `PERIOD_MISMATCH`), and CAC payback
        (a deliberate `MISSING_INPUTS`, pending a real input source).
    """
    results: list[DerivedMetricResult] = []
    results.extend(_ratio_series(facts, M.LTV, M.CAC, "ltv_cac_ratio", "LTV", "CAC"))
    results.extend(
        _ratio_series(
            facts, M.REVENUE, M.REGISTERED_CUSTOMERS, "revenue_per_registered_customer", "Revenue",
            "Registered Customers", display="currency",
        )
    )
    results.extend(
        _ratio_series(
            facts, M.REVENUE, M.MONTHLY_ACTIVE_USERS, "revenue_per_mau", "Revenue",
            "Monthly Active Users", display="currency",
        )
    )
    results.extend(
        _ratio_series(facts, M.REVENUE, M.ORDERS, "revenue_per_order", "Revenue", "Orders", display="currency")
    )
    results.append(_orders_per_active_user(facts))
    results.append(_cac_payback(facts))
    return results


# ---------------------------------------------------------------------------
# Valuation metrics
# ---------------------------------------------------------------------------


def calculate_valuation_metrics(facts: list[FactPoint]) -> list[DerivedMetricResult]:
    """Compute all valuation-related metrics.

    Args:
        facts: The full set of financial facts for a document.

    Returns:
        A flat list covering valuation/revenue, valuation/EBITDA,
        revenue per dollar raised, and funding as a percentage of
        post-money valuation.
    """
    results: list[DerivedMetricResult] = []
    results.extend(
        _ratio_series(
            facts, M.VALUATION_POST_MONEY, M.REVENUE, "valuation_to_revenue",
            "Post-Money Valuation", "Revenue",
        )
    )
    results.extend(
        _ratio_series(
            facts, M.VALUATION_POST_MONEY, M.EBITDA, "valuation_to_ebitda",
            "Post-Money Valuation", "EBITDA",
        )
    )
    results.extend(
        _ratio_series(
            facts, M.REVENUE, M.FUNDING_AMOUNT, "revenue_per_dollar_raised",
            "Revenue", "Funding Amount",
        )
    )
    results.extend(
        _ratio_series(
            facts, M.FUNDING_AMOUNT, M.VALUATION_POST_MONEY, "funding_pct_of_post_money",
            "Funding Amount", "Post-Money Valuation",
        )
    )
    return results


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def calculate_all_derived_metrics(facts: list[FactPoint]) -> list[DerivedMetricResult]:
    """Compute every derived metric across all four categories.

    Args:
        facts: The full set of financial facts for a document.

    Returns:
        The combined, flat list of all growth, profitability,
        unit-economics, and valuation results.
    """
    return [
        *calculate_growth_metrics(facts),
        *calculate_profitability_metrics(facts),
        *calculate_unit_economics_metrics(facts),
        *calculate_valuation_metrics(facts),
    ]


# ---------------------------------------------------------------------------
# ORM-facing conversion (thin, separately testable)
# ---------------------------------------------------------------------------


def facts_from_financial_facts(orm_facts: list) -> list[FactPoint]:
    """Convert `FinancialFact` ORM rows into `FactPoint`s for the engine.

    Kept as a single, small, easily-mocked conversion point so the
    calculation engine above never imports SQLAlchemy or touches a
    session — `orm_facts` is typed loosely (`list`) rather than
    `list[FinancialFact]` to avoid a hard import dependency in this
    module; callers pass already-fetched `FinancialFact` rows.

    Args:
        orm_facts: A list of `FinancialFact` ORM instances.

    Returns:
        The equivalent list of `FactPoint`s.
    """
    return [
        FactPoint(
            metric=f.metric,
            value=f.value,
            period=f.period,
            period_type=f.period_type,
            value_type=f.value_type,
            currency=f.currency,
            source_citation_id=str(f.source_citation_id) if f.source_citation_id else None,
        )
        for f in orm_facts
    ]