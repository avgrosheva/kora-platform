"""Analytical chat with backend-orchestrated tool calling (Section 8).

Runs a bounded tool-calling loop: the model can request scoped,
read-only operations (`app.services.chat_tools`) instead of receiving
only pre-retrieved chunks. This service owns the loop — the LLM
proposes tool calls, this service executes them via existing services,
and feeds results back until the model produces a final answer or the
call limit is reached. No conversation memory is persisted (matches
the original chat milestone's constraint); each request is self-
contained, though within one request multiple back-and-forth turns
with the model are allowed to satisfy the tool-calling protocol.
"""

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.schemas.chat import ChatSource
from app.schemas.chat_v2 import ChatV2Response, ToolCallRecord
from app.services.ai_service import AIService
from app.services.chat_tools import (
    TOOL_SPECS,
    execute_calculate_metric,
    execute_get_financial_time_series,
    execute_get_missing_information,
    execute_search_document_chunks,
)

settings = get_settings()

MAX_TOOL_ROUNDS = 4

_SYSTEM_PROMPT = """You are an analytical assistant helping investors evaluate \
companies using the tools provided.

Rules:
- Use the provided tools to retrieve information rather than relying on \
your own knowledge or assumptions.
- For any calculated figure (growth rates, ratios, margins), ALWAYS call \
calculate_metric rather than computing it yourself — you do not have \
reliable arithmetic and must not present an estimate as a precise figure.
- If a tool returns no data or an error, say so plainly rather than \
guessing.
- Base your final answer only on tool results and the conversation so far. \
If nothing found relates to the question, say you don't know.
- Once you have enough information, provide a clear, direct answer. Do not \
call more tools than necessary."""


class ChatV2Service:
    """Orchestrates a bounded tool-calling conversation for one question."""

    @staticmethod
    async def answer_question_with_tools(
        db: AsyncSession,
        organization_id: uuid.UUID,
        document_id: uuid.UUID | None,
        actor_id: uuid.UUID,
        question: str,
    ) -> ChatV2Response:
        """Answer a question, allowing the model to call scoped tools.

        Args:
            db: The active database session.
            organization_id: The organization in scope.
            document_id: The document in scope, or `None` for
                organization-wide questions (document-specific tools
                will return an explanatory error if invoked without
                one).
            actor_id: The requesting user's id.
            question: The user's question.

        Returns:
            The final answer, accumulated sources, a full record of
            every tool call made, and the model used.

        Raises:
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured.
            AIRequestFailedError: If any completion request fails
                after its own retry.
        """
        messages: list[dict] = [{"role": "user", "content": question}]
        all_sources: list[ChatSource] = []
        tool_call_records: list[ToolCallRecord] = []

        for _ in range(MAX_TOOL_ROUNDS):
            answer, tool_calls = await AIService.generate_chat_answer_with_tools(
                _SYSTEM_PROMPT, messages, TOOL_SPECS
            )

            if not tool_calls:
                return ChatV2Response(
                    answer=(answer or "").strip(),
                    sources=all_sources,
                    tool_calls=tool_call_records,
                    model_used=settings.OPENAI_MODEL,
                )

            messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            })

            for tool_call in tool_calls:
                arguments = json.loads(tool_call.function.arguments or "{}")
                summary, tool_result_payload, extra_sources = await _dispatch_tool(
                    db, organization_id, document_id, actor_id, tool_call.function.name, arguments
                )
                if extra_sources:
                    all_sources.extend(extra_sources)
                tool_call_records.append(
                    ToolCallRecord(tool_name=tool_call.function.name, arguments=arguments, result_summary=summary)
                )
                messages.append({
                    "role": "tool", "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result_payload),
                })

        return ChatV2Response(
            answer="I wasn't able to fully answer this within the allowed number of tool calls. Please try a more specific question.",
            sources=all_sources, tool_calls=tool_call_records, model_used=settings.OPENAI_MODEL,
        )


async def _dispatch_tool(
    db: AsyncSession,
    organization_id: uuid.UUID,
    document_id: uuid.UUID | None,
    actor_id: uuid.UUID,
    tool_name: str,
    arguments: dict,
) -> tuple[str, dict, list[ChatSource]]:
    """Dispatch a single tool call to its implementation.

    Args:
        db: The active database session.
        organization_id: The organization in scope.
        document_id: The document in scope, or `None`.
        actor_id: The requesting user's id.
        tool_name: Which tool the model requested.
        arguments: The model-supplied arguments.

    Returns:
        A tuple of `(summary, tool_result_payload, extra_sources)`.
    """
    if tool_name == "search_document_chunks":
        summary, sources, tool_result = await execute_search_document_chunks(
            db, organization_id, actor_id, arguments
        )
        return summary, tool_result, sources
    if tool_name == "get_financial_time_series":
        summary, tool_result = await execute_get_financial_time_series(db, document_id, arguments)
        return summary, tool_result, []
    if tool_name == "calculate_metric":
        summary, tool_result = await execute_calculate_metric(db, document_id, arguments)
        return summary, tool_result, []
    if tool_name == "get_missing_information":
        summary, tool_result = await execute_get_missing_information(db, document_id, arguments)
        return summary, tool_result, []

    return f"Unknown tool: {tool_name}", {"error": f"Unknown tool: {tool_name}"}, []