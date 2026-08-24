"""Scoped, backend-orchestrated tools for analytical chat (Section 8).

Each tool is a plain async function wrapping an already-built service —
`RetrievalService`, `FinancialFactsService`, `derived_metrics_service`,
`missing_information_service`. The LLM never executes arbitrary code or
touches the database: it can only request one of these fixed,
read-only, pre-scoped operations, and every call is logged into the
`ToolCallRecord` list returned to the API consumer for transparency.

Tool definitions (`TOOL_SPECS`) follow the OpenAI function-calling
schema shape, but are interpreted entirely by this module's own
dispatch loop in `chat_v2_service.py` — no tool implementation is ever
handed directly to the OpenAI client as executable code.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_fact import FinancialMetricType
from app.services.derived_metrics_service import calculate_all_derived_metrics
from app.services.financial_facts_service import FinancialFactsService
from app.services.missing_information_service import compute_missing_information, facts_to_metric_set
from app.services.retrieval_service import RetrievalService

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_document_chunks",
            "description": (
                "Search the organization's indexed documents for text semantically "
                "relevant to a query. Use this for qualitative questions about "
                "business model, market, competitors, risks, or anything requiring "
                "the source document's actual wording."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "top_k": {"type": "integer", "description": "Max results (1-10).", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_time_series",
            "description": (
                "Get all recorded values for a specific financial metric across all "
                "periods for the current document. Use this for questions about "
                "revenue, EBITDA, cash, growth, or any raw financial figure by year."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": [m.value for m in FinancialMetricType],
                        "description": "Which metric to retrieve.",
                    },
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_metric",
            "description": (
                "Get a specific calculated/derived metric (e.g. YoY growth, CAGR, "
                "LTV/CAC ratio, EBITDA margin) for the current document. This is "
                "deterministic — never estimate these yourself; always call this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "description": (
                            "The derived metric identifier, e.g. 'revenue_yoy_growth', "
                            "'revenue_cagr', 'ltv_cac_ratio', 'ebitda_margin'."
                        ),
                    },
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_missing_information",
            "description": (
                "Get the checklist of information that is missing or not yet found "
                "for the current document, grouped by category. Use this when asked "
                "what data is missing, incomplete, or still needed for due diligence."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


async def execute_search_document_chunks(
    db: AsyncSession, organization_id: uuid.UUID, actor_id: uuid.UUID, arguments: dict
) -> tuple[str, list, dict]:
    """Execute the `search_document_chunks` tool.

    Args:
        db: The active database session.
        organization_id: The organization to search within.
        actor_id: The requesting user's id.
        arguments: The model-supplied arguments (`query`, optional `top_k`).

    Returns:
        A tuple of `(summary_text, chat_sources, tool_result_for_model)`.
    """
    query = arguments.get("query", "")
    top_k = min(int(arguments.get("top_k", 5)), 10)

    results = await RetrievalService.semantic_search(db, organization_id, actor_id, query, top_k)

    from app.schemas.chat import ChatSource
    sources = [
        ChatSource(
            document_id=r.document_id, chunk_index=r.chunk_index,
            similarity_score=r.similarity_score, snippet=r.text[:300],
        )
        for r in results
    ]
    tool_result = {
        "results": [{"text": r.text, "similarity_score": r.similarity_score} for r in results]
    }
    summary = f"Found {len(results)} relevant excerpt(s) for query {query!r}."
    return summary, sources, tool_result


async def execute_get_financial_time_series(
    db: AsyncSession, document_id: uuid.UUID | None, arguments: dict
) -> tuple[str, dict]:
    """Execute the `get_financial_time_series` tool.

    Args:
        db: The active database session.
        document_id: The document in scope, or `None` if the request
            wasn't document-scoped (the tool returns an explanatory
            error result in that case, rather than guessing a document).
        arguments: The model-supplied arguments (`metric`).

    Returns:
        A tuple of `(summary_text, tool_result_for_model)`.
    """
    if document_id is None:
        return "No document is in scope for this question.", {
            "error": "This question requires a specific document to be selected."
        }

    metric_name = arguments.get("metric", "")
    fact_points = await FinancialFactsService.get_fact_points(db, document_id)
    try:
        metric = FinancialMetricType(metric_name)
    except ValueError:
        return f"Unknown metric {metric_name!r}.", {"error": f"Unknown metric: {metric_name}"}

    matches = sorted(
        [f for f in fact_points if f.metric == metric], key=lambda f: f.period or ""
    )
    tool_result = {
        "metric": metric_name,
        "values": [
            {"period": f.period, "value": f.value, "value_type": f.value_type.value, "currency": f.currency}
            for f in matches
        ],
    }
    summary = f"Found {len(matches)} value(s) for {metric_name}."
    return summary, tool_result


async def execute_calculate_metric(
    db: AsyncSession, document_id: uuid.UUID | None, arguments: dict
) -> tuple[str, dict]:
    """Execute the `calculate_metric` tool.

    Args:
        db: The active database session.
        document_id: The document in scope, or `None`.
        arguments: The model-supplied arguments (`metric_name`).

    Returns:
        A tuple of `(summary_text, tool_result_for_model)`.
    """
    if document_id is None:
        return "No document is in scope for this question.", {
            "error": "This question requires a specific document to be selected."
        }

    metric_name = arguments.get("metric_name", "")
    fact_points = await FinancialFactsService.get_fact_points(db, document_id)
    all_results = calculate_all_derived_metrics(fact_points)
    matches = [r for r in all_results if r.metric == metric_name]

    if not matches:
        return f"No result found for {metric_name!r}.", {"error": f"Unknown or uncomputed metric: {metric_name}"}

    tool_result = {
        "results": [
            {
                "period": r.period, "value": r.value, "display_value": r.display_value,
                "status": r.status.value, "formula": r.formula, "notes": r.notes,
            }
            for r in matches
        ]
    }
    summary = f"Calculated {metric_name}: {matches[0].display_value or matches[0].status.value}."
    return summary, tool_result


async def execute_get_missing_information(
    db: AsyncSession, document_id: uuid.UUID | None, arguments: dict
) -> tuple[str, dict]:
    """Execute the `get_missing_information` tool.

    Args:
        db: The active database session.
        document_id: The document in scope, or `None`.
        arguments: Unused; the tool takes no arguments.

    Returns:
        A tuple of `(summary_text, tool_result_for_model)`.
    """
    if document_id is None:
        return "No document is in scope for this question.", {
            "error": "This question requires a specific document to be selected."
        }

    fact_points = await FinancialFactsService.get_fact_points(db, document_id)
    result = compute_missing_information(
        financial_metrics_found=facts_to_metric_set(fact_points),
        company_fields_found=set(),
        market_fields_found=set(),
        team_fields_found=set(),
    )
    tool_result = {
        "by_category": [
            {"category": c.category, "missing": c.missing} for c in result.by_category if c.missing
        ]
    }
    summary = f"{result.total_required - result.total_found} of {result.total_required} checklist items are missing."
    return summary, tool_result