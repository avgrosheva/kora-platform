"""Shared MarketGo fixture data, used across derived-metrics and
(in later steps) validation-service and integration tests.

These are exactly the figures from the MarketGo source document, so
every test in the suite is checking against the same, real-world-shaped
numbers rather than synthetic round figures that might hide edge cases.
"""

from app.models.financial_fact import FinancialMetricType as M
from app.models.financial_fact import FinancialValueType as V
from app.models.financial_fact import PeriodType as P
from app.services.derived_metrics_service import FactPoint


def marketgo_facts() -> list[FactPoint]:
    """Build the full MarketGo fixture fact set.

    Returns:
        A list of `FactPoint`s matching every figure stated in the
        MarketGo source document.
    """
    return [
        FactPoint(M.REVENUE, 24_000_000, "2023", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.REVENUE, 58_000_000, "2024", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.REVENUE, 96_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.GROSS_MARGIN, 0.22, "2024", P.YEAR, V.ACTUAL),
        FactPoint(M.GROSS_MARGIN, 0.29, "2025", P.YEAR, V.ACTUAL),
        FactPoint(M.EBITDA, -6_000_000, "2024", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.EBITDA, 8_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.NET_INCOME, 3_500_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.CASH, 18_000_000, "2025", P.POINT_IN_TIME, V.ACTUAL, "USD"),
        FactPoint(M.OPERATING_EXPENSES, 88_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.CAC, 27, "2024", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.CAC, 21, "2025", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.LTV, 170, "2025", P.YEAR, V.ESTIMATE, "USD"),
        FactPoint(M.ORDERS, 8_700_000, "2024", P.YEAR, V.ACTUAL),
        FactPoint(M.ORDERS, 14_500_000, "2025", P.YEAR, V.ACTUAL),
        FactPoint(M.AOV, 31, "2024", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.AOV, 34, "2025", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.REGISTERED_CUSTOMERS, 2_800_000, "2025", P.YEAR, V.ACTUAL),
        FactPoint(M.MONTHLY_ACTIVE_USERS, 620_000, "2025", P.YEAR, V.ACTUAL),
        FactPoint(M.FUNDING_AMOUNT, 45_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
        FactPoint(M.VALUATION_POST_MONEY, 280_000_000, "2025", P.YEAR, V.ACTUAL, "USD"),
    ]