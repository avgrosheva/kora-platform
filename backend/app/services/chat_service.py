"""Single-turn RAG chat over an organization's indexed documents.

Retrieves relevant chunks via the existing `RetrievalService`, builds a
context-grounded prompt, and calls `AIService` to generate an answer.
This layer performs no new retrieval logic — it is a thin consumer of
the RAG infrastructure built in the previous milestone. No conversation
memory or chat history is stored; each call is fully self-contained.
Services operate directly on `AsyncSession` — there is no repository
layer in this project's architecture.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.schemas.chat import ChatResponse, ChatSource
from app.schemas.rag import SearchResultRead
from app.services.ai_service import AIService
from app.services.retrieval_service import RetrievalService

settings = get_settings()

SNIPPET_MAX_CHARS = 300

NO_CONTEXT_ANSWER = (
    "I don't know. I couldn't find any relevant information in the "
    "organization's indexed documents to answer this question."
)
NO_CONTEXT_MODEL_SENTINEL = "none"
"""Returned as `model_used` when no context was found and the LLM was
never called — makes it explicit to the caller that this is a
deterministic fallback, not a genuine model-generated "I don't know"."""

_CHAT_SYSTEM_PROMPT = """You are a research assistant answering \
questions about companies using only the provided document excerpts.

Answer ONLY using the information in the provided context below. Do \
not use any outside knowledge, and do not make assumptions beyond what \
is explicitly stated.

If the answer is not present in the context, say you don't know. Do \
not guess, and do not fabricate information under any circumstances.

When you use information from a specific excerpt, you may refer to it \
by its number (e.g. "According to excerpt 2...")."""


def _truncate_snippet(text: str) -> str:
    """Truncate chunk text to a citation-friendly length.

    Args:
        text: The full chunk text.

    Returns:
        The text, truncated to `SNIPPET_MAX_CHARS` characters with an
        ellipsis appended if truncation occurred.
    """
    if len(text) <= SNIPPET_MAX_CHARS:
        return text
    return text[:SNIPPET_MAX_CHARS].rstrip() + "..."


def build_chat_prompt(
    question: str, chunks: list[SearchResultRead]
) -> tuple[str, str]:
    """Build the system prompt and user message for a chat answer.

    This is a pure function of its inputs — the same `question` and
    `chunks` (in the same order) always produce byte-identical output,
    with no timestamps, randomness, or other non-deterministic content.
    Kept separate from `ChatService.answer_question` so prompt
    construction can be unit-tested without any database or network
    access.

    Args:
        question: The user's question.
        chunks: The retrieved chunks to use as context, in the order
            they should be presented to the model (highest similarity
            first, as returned by `RetrievalService`).

    Returns:
        A tuple of `(system_prompt, user_message)`.
    """
    context_blocks = "\n\n".join(
        f"[Excerpt {index + 1}] (document {chunk.document_id}, "
        f"chunk {chunk.chunk_index}):\n{chunk.text}"
        for index, chunk in enumerate(chunks)
    )

    user_message = (
        f"Context:\n{context_blocks}\n\n"
        f"Question: {question}\n\n"
        f"Answer the question using only the context above. If the "
        f"answer is not present in the context, say you don't know."
    )

    return _CHAT_SYSTEM_PROMPT, user_message


class ChatService:
    """Single-turn RAG chat: retrieve, build prompt, generate answer."""

    NO_CONTEXT_MODEL_SENTINEL = NO_CONTEXT_MODEL_SENTINEL

    @staticmethod
    async def answer_question(
        db: AsyncSession,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        question: str,
        top_k: int,
    ) -> ChatResponse:
        """Answer a question using retrieval-augmented generation.

        Retrieval and access control are entirely delegated to
        `RetrievalService.semantic_search` — this method performs no
        separate organization-membership check and runs no additional
        search queries.

        If no relevant chunks are found, the LLM is never called: a
        fixed "I don't know" answer is returned immediately. This
        avoids an unnecessary API call and guarantees the model can
        never hallucinate an answer when there is genuinely no context
        to ground it in.

        Args:
            db: The active database session.
            organization_id: The organization to search and answer
                within.
            actor_id: The id of the requesting user.
            question: The user's question.
            top_k: The maximum number of chunks to retrieve as context.

        Returns:
            The generated answer, its supporting sources, and the model
            identifier used (or the no-context sentinel).

        Raises:
            OrganizationAccessDeniedError: If the actor is not a member
                of the organization (propagated from
                `RetrievalService`).
            EmbeddingServiceNotConfiguredError: If no OpenAI API key is
                configured for embeddings (propagated from
                `RetrievalService`).
            EmbeddingRequestFailedError: If the question's embedding
                request fails after retrying once (propagated from
                `RetrievalService`).
            InvalidEmbeddingDimensionError: If the question's embedding
                has the wrong dimensionality (propagated from
                `RetrievalService`).
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured for chat completion, or it is rejected as
                invalid (propagated from `AIService`).
            AIRequestFailedError: If the chat completion request fails
                after retrying once (propagated from `AIService`).
        """
        chunks = await RetrievalService.semantic_search(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            query=question,
            top_k=top_k,
        )

        if not chunks:
            return ChatResponse(
                answer=NO_CONTEXT_ANSWER,
                sources=[],
                model_used=NO_CONTEXT_MODEL_SENTINEL,
            )

        system_prompt, user_message = build_chat_prompt(question, chunks)
        answer_text = await AIService.generate_chat_answer(
            system_prompt, user_message
        )

        sources = [
            ChatSource(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                similarity_score=chunk.similarity_score,
                snippet=_truncate_snippet(chunk.text),
            )
            for chunk in chunks
        ]

        return ChatResponse(
            answer=answer_text.strip(),
            sources=sources,
            model_used=settings.OPENAI_MODEL,
        )