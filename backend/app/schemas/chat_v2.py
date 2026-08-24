"""Pydantic schemas for the tool-calling analytical chat layer."""

import uuid

from pydantic import BaseModel, Field

from app.schemas.chat import ChatSource


class ChatV2Request(BaseModel):
    """Payload for an analytical chat question, optionally scoped to one document.

    Attributes:
        organization_id: The organization whose data is in scope.
        document_id: If provided, tools are scoped to this single
            document in addition to organization-wide retrieval;
            financial-fact and calculation tools require this to be
            set.
        question: The user's question.
    """

    organization_id: uuid.UUID
    document_id: uuid.UUID | None = None
    question: str = Field(min_length=1)


class ToolCallRecord(BaseModel):
    """A record of one tool invocation made while answering a question.

    Attributes:
        tool_name: Which tool was called.
        arguments: The arguments the model supplied.
        result_summary: A short, human-readable summary of what the
            tool returned (not the full raw result, to keep the
            response payload manageable).
    """

    tool_name: str
    arguments: dict
    result_summary: str


class ChatV2Response(BaseModel):
    """Response for `POST /chat/v2`.

    Attributes:
        answer: The generated answer.
        sources: Document excerpts retrieved via
            `search_document_chunks`, if that tool was used.
        tool_calls: Every tool invocation made while answering,
            exposed for transparency (Section 8's "must be traceable").
        model_used: The model identifier used for the final answer.
    """

    answer: str
    sources: list[ChatSource]
    tool_calls: list[ToolCallRecord]
    model_used: str