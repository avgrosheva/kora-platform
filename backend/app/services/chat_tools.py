"""Scoped, backend-orchestrated tools for analytical chat (Section 8).

Each tool is a plain async function wrapping an already-built service —
`RetrievalService`, `FinancialFactsService`, `derived_metrics_service`,
`missing_information_service`, and (Evidence Layer plan, Step 10)
`EvidenceService`, `FindingsService`, `QualitativeFactsService`. The LLM
never executes arbitrary code or touches the database: it can only
request one of these fixed, read-only, pre-scoped operations, and every
call is logged into the `ToolCallRecord` list returned to the API
consumer for transparency.

Tool definitions (`TOOL_SPECS`) follow the OpenAI function-calling
schema shape, but are interpreted entirely by this module's own
dispatch loop in `chat_v2_service.py` — no tool implementation is ever
handed directly to the OpenAI client as executable code.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.financial_fact import FinancialMetricType
from app.schemas.missing_information import MissingInformationResponse
from app.services.derived_metrics_service import calculate_all_derived_metrics
from app.services.document_service import DocumentService
from app.services.evidence_service import EvidenceService
from app.services.financial_facts_service import FinancialFactsService
from app.services.findings_service import FindingsService
from app.services.missing_information_service import compute_missing_information
from app.services.qualitative_facts_service import QualitativeFactsService
from app.services.retrieval_service import RetrievalService

# Caps how many documents an organization-wide tool call (no specific
# document selected) will fan out to. The chat UI currently has no way
# to select a document at all (see chat_v2_service.py's module
# docstring), so this is the only path these tools have — but it must
# still not turn one chat question into dozens of per-document queries
# for an organization with a large document library.
_MAX_ORG_WIDE_DOCUMENTS = 15

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
                "what data is missing, incomplete, or still needed for due diligence. "
                "If no specific document is selected in this conversation, this returns "
                "one checklist per completed document in the organization instead (a "
                "'documents' list, each entry tagged with document_id/document_name) — "
                "state which document(s) your answer covers rather than presenting one "
                "company's gaps as if they applied to the whole organization."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_findings",
            "description": (
                "Get every finding for the current document: deterministic "
                "consistency/anomaly checks, document-stated risk claims, and Kora's "
                "own inference-rule findings, each with a severity and an explicit "
                "type (deterministic / document_stated / ai_inferred). Use this for "
                "any question about risks, red flags, issues, or concerns with the "
                "document. ALWAYS check each result's type before answering: a "
                "document_stated finding is something the document itself says; an "
                "ai_inferred finding is Kora's own conclusion and must be presented "
                "as such, never as a fact the document states. If no specific document "
                "is selected in this conversation, this returns findings across every "
                "completed document in the organization, each tagged with "
                "document_id/document_name — always say which company/document a "
                "finding belongs to, never merge findings from different documents "
                "into one unattributed answer."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_qualitative_facts",
            "description": (
                "Get every extracted non-numeric claim for the current document — "
                "customer/legal/operational/IP/team/market risk claims AND growth "
                "opportunities — each with its category, severity (if it's a risk), "
                "and confidence. Use this for questions about specific qualitative "
                "claims or opportunities mentioned in the document, including "
                "opportunities (which get_findings does not include, since an "
                "opportunity is not a risk finding). If no specific document is "
                "selected in this conversation, this returns facts across every "
                "completed document in the organization, each tagged with "
                "document_id/document_name — attribute each claim to its document."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


async def _completed_org_documents(
    db: AsyncSession, organization_id: uuid.UUID, actor_id: uuid.UUID
) -> list[Document]:
    """List an organization's fully-processed documents, most recent first.

    Shared by every tool below that falls back to an organization-wide
    answer when no specific document is in scope — capped at
    `_MAX_ORG_WIDE_DOCUMENTS`. Only `COMPLETED` documents are considered,
    since anything else has no text (and therefore no facts) to look at.

    Args:
        db: The active database session.
        organization_id: The organization to list documents for.
        actor_id: The requesting user's id (membership is re-checked
            here, same as every other organization-scoped read).

    Returns:
        Up to `_MAX_ORG_WIDE_DOCUMENTS` completed documents.
    """
    documents = await DocumentService.list_documents(db, organization_id, actor_id)
    completed = [doc for doc in documents if doc.status == DocumentStatus.COMPLETED]
    return completed[:_MAX_ORG_WIDE_DOCUMENTS]


def _compute_missing_for_evidence(evidence: list) -> MissingInformationResponse:
    """Run `compute_missing_information` over one document's evidence.

    Factored out so both the single-document and organization-wide
    branches of `execute_get_missing_information` share the exact same
    found/missing computation, through `EvidenceService`.

    Args:
        evidence: One document's `EvidenceFact` list.

    Returns:
        The computed checklist result.
    """
    return compute_missing_information(
        financial_metrics_found={
            FinancialMetricType(fact.field_name) for fact in evidence if fact.category == "financial"
        },
        company_fields_found={fact.field_name for fact in evidence if fact.category == "company"},
        market_fields_found={fact.field_name for fact in evidence if fact.category == "market"},
        team_fields_found={fact.field_name for fact in evidence if fact.category == "team"},
    )


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
    db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID | None, actor_id: uuid.UUID, arguments: dict
) -> tuple[str, dict]:
    """Execute the `get_missing_information` tool.

    Reads found fields through `EvidenceService`, the same facade
    `GET /documents/{id}/missing-information` uses (Step 2) — this tool
    previously hardcoded `company_fields_found`/`market_fields_found`/
    `team_fields_found` to empty sets exactly like Bug B's endpoint did
    before that fix, so the chat could tell a user every company/market
    field was missing even when Coverage correctly showed it as found.
    That instance of Bug B was never fixed here at the time; fixed now.

    Falls back to every completed document in the organization when no
    specific document is selected — the chat UI currently has no way to
    select one at all, so without this fallback this tool always
    returned "no document in scope" in practice, not just in an edge
    case.

    Args:
        db: The active database session.
        organization_id: The organization in scope.
        document_id: The document in scope, or `None` for an
            organization-wide answer.
        actor_id: The requesting user's id.
        arguments: Unused; the tool takes no arguments.

    Returns:
        A tuple of `(summary_text, tool_result_for_model)`. Single-
        document results keep the original flat `by_category` shape;
        organization-wide results are a list of per-document
        `by_category` breakdowns, each tagged with the document it
        concerns.
    """
    if document_id is not None:
        evidence = await EvidenceService.get_evidence(db, document_id)
        result = _compute_missing_for_evidence(evidence)
        tool_result = {
            "by_category": [
                {"category": c.category, "missing": c.missing} for c in result.by_category if c.missing
            ]
        }
        summary = f"{result.total_required - result.total_found} of {result.total_required} checklist items are missing."
        return summary, tool_result

    documents = await _completed_org_documents(db, organization_id, actor_id)
    if not documents:
        return "No processed documents found in this organization.", {"error": "no_processed_documents"}

    per_document = []
    for doc in documents:
        evidence = await EvidenceService.get_evidence(db, doc.id)
        result = _compute_missing_for_evidence(evidence)
        per_document.append({
            "document_id": str(doc.id),
            "document_name": doc.original_filename,
            "by_category": [
                {"category": c.category, "missing": c.missing} for c in result.by_category if c.missing
            ],
        })
    summary = f"Missing-information checklist computed for {len(documents)} document(s) in the organization."
    return summary, {"documents": per_document}


async def execute_get_findings(
    db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID | None, actor_id: uuid.UUID, arguments: dict
) -> tuple[str, dict]:
    """Execute the `get_findings` tool.

    Falls back to every completed document in the organization when no
    specific document is selected (see `execute_get_missing_information`
    for why this fallback exists at all) — each finding is tagged with
    the document it came from so the model can never conflate two
    different companies' risks into one answer.

    Args:
        db: The active database session.
        organization_id: The organization in scope.
        document_id: The document in scope, or `None` for an
            organization-wide answer.
        actor_id: The requesting user's id.
        arguments: Unused; the tool takes no arguments.

    Returns:
        A tuple of `(summary_text, tool_result_for_model)`. Every
        finding's `type` is included explicitly so the model can (and,
        per the tool description and system prompt, must) distinguish
        a document-stated claim from Kora's own inference.
    """
    if document_id is not None:
        pairs: list[tuple[Document | None, object]] = [
            (None, finding) for finding in await FindingsService.get_findings(db, document_id)
        ]
    else:
        documents = await _completed_org_documents(db, organization_id, actor_id)
        if not documents:
            return "No processed documents found in this organization.", {"error": "no_processed_documents"}
        pairs = [
            (doc, finding)
            for doc in documents
            for finding in await FindingsService.get_findings(db, doc.id)
        ]

    tool_result = {
        "findings": [
            {
                "document_id": str(doc.id) if doc else None,
                "document_name": doc.original_filename if doc else None,
                "title": f.title, "category": f.category, "severity": f.severity.value, "type": f.type.value,
                "evidence": f.evidence, "explanation": f.explanation, "implication": f.implication,
                "recommended_next_step": f.recommended_next_step,
            }
            for doc, f in pairs
        ]
    }
    critical_or_high = sum(1 for _, f in pairs if f.severity.value in ("critical", "high"))
    scope_note = "" if document_id is not None else f" across {len({d.id for d, _ in pairs if d})} document(s)"
    summary = f"Found {len(pairs)} finding(s){scope_note}, {critical_or_high} critical/high severity."
    return summary, tool_result


async def execute_get_qualitative_facts(
    db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID | None, actor_id: uuid.UUID, arguments: dict
) -> tuple[str, dict]:
    """Execute the `get_qualitative_facts` tool.

    Falls back to every completed document in the organization when no
    specific document is selected — see `execute_get_missing_information`.

    Args:
        db: The active database session.
        organization_id: The organization in scope.
        document_id: The document in scope, or `None` for an
            organization-wide answer.
        actor_id: The requesting user's id.
        arguments: Unused; the tool takes no arguments.

    Returns:
        A tuple of `(summary_text, tool_result_for_model)`.
    """
    if document_id is not None:
        pairs: list[tuple[Document | None, object]] = [
            (None, fact) for fact in await QualitativeFactsService.list_facts(db, document_id)
        ]
    else:
        documents = await _completed_org_documents(db, organization_id, actor_id)
        if not documents:
            return "No processed documents found in this organization.", {"error": "no_processed_documents"}
        pairs = [
            (doc, fact)
            for doc in documents
            for fact in await QualitativeFactsService.list_facts(db, doc.id)
        ]

    tool_result = {
        "facts": [
            {
                "document_id": str(doc.id) if doc else None,
                "document_name": doc.original_filename if doc else None,
                "category": f.category, "claim_text": f.claim_text, "fact_type": f.fact_type,
                "severity_hint": f.severity_hint, "confidence": f.confidence,
            }
            for doc, f in pairs
        ]
    }
    summary = f"Found {len(pairs)} qualitative fact(s)."
    return summary, tool_result