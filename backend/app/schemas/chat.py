"""Pydantic schemas for the AI chat layer."""

import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for asking a question over an organization's documents.

    Attributes:
        organization_id: The organization whose indexed documents to
            search and answer from.
        question: The user's natural-language question.
        top_k: The maximum number of retrieved chunks to use as
            context (1-20). Defaults to 5.
    """

    organization_id: uuid.UUID
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ChatSource(BaseModel):
    """A single retrieved chunk cited in support of a chat answer.

    Attributes:
        document_id: The id of the document this chunk belongs to.
        chunk_index: The chunk's position within its source document.
        similarity_score: Cosine similarity between the question and
            this chunk, as returned by `RetrievalService`.
        snippet: The (possibly truncated) chunk text, shown as a
            citation for the answer.
    """

    document_id: uuid.UUID
    chunk_index: int
    similarity_score: float
    snippet: str


class ChatResponse(BaseModel):
    """Response for `POST /chat`.

    Attributes:
        answer: The generated answer, grounded only in the retrieved
            context. If no relevant context was found, this is a fixed
            "I don't know" statement.
        sources: The chunks retrieved and used to construct the answer,
            in the same order they were provided to the model
            (highest similarity first). Empty if no relevant context
            was found.
        model_used: The identifier of the model that generated the
            answer, or a sentinel value indicating no model call was
            made (see `ChatService.NO_CONTEXT_MODEL_SENTINEL`).
    """

    answer: str
    sources: list[ChatSource]
    model_used: str