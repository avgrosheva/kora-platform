"""Embedding generation for document chunks and search queries.

Defines the `EmbeddingProvider` interface and an OpenAI-backed
implementation. `EmbeddingService` depends only on the interface, so a
future provider (a different API, a local model, etc.) can be
substituted without changing any calling code — the same
replaceability pattern used by `ScoringStrategy` in the investment
scoring milestone.
"""

import asyncio
from abc import ABC, abstractmethod

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.config import get_settings
from app.core.logging import get_logger
from app.core.rag_config import EMBEDDING_DIMENSIONS

logger = get_logger(__name__)
settings = get_settings()

_RETRY_DELAY_SECONDS = 1.0


class EmbeddingServiceError(Exception):
    """Base exception for embedding generation failures."""


class EmbeddingServiceNotConfiguredError(EmbeddingServiceError):
    """Raised when no OpenAI API key is configured, or the configured
    key is rejected as invalid."""


class EmbeddingRequestFailedError(EmbeddingServiceError):
    """Raised when the embeddings request fails after the allowed retry,
    due to a timeout, connection error, or rate limiting."""


class InvalidEmbeddingDimensionError(EmbeddingServiceError):
    """Raised when a returned embedding's dimensionality does not match
    `EMBEDDING_DIMENSIONS`."""


class EmbeddingProvider(ABC):
    """Interface for generating vector embeddings from text.

    Any future embedding backend implements this interface, which is
    the sole seam `EmbeddingService` depends on.
    """

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: The texts to embed, in order.

        Returns:
            A list of embedding vectors, in the same order as `texts`.
        """


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Generates embeddings via the OpenAI Embeddings API.

    Requests are batched to respect API limits, and each batch is
    retried once on transient failures (timeout, connection error, rate
    limit), mirroring the retry behavior already established in
    `ai_service.py`.
    """

    MODEL = "text-embedding-3-small"
    MAX_BATCH_SIZE = 100
    REQUEST_TIMEOUT_SECONDS = 60.0

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts via OpenAI.

        Args:
            texts: The texts to embed, in order.

        Returns:
            A list of embedding vectors, in the same order as `texts`.
            Returns an empty list if `texts` is empty.

        Raises:
            EmbeddingServiceNotConfiguredError: If no OpenAI API key is
                configured, or it is rejected as invalid.
            EmbeddingRequestFailedError: If a batch request fails after
                retrying once.
            InvalidEmbeddingDimensionError: If any returned embedding
                does not have `EMBEDDING_DIMENSIONS` dimensions.
        """
        if not texts:
            return []

        if not settings.OPENAI_API_KEY:
            raise EmbeddingServiceNotConfiguredError(
                "OPENAI_API_KEY is not configured. Embedding generation "
                "is unavailable until an API key is set."
            )

        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )

        all_vectors: list[list[float]] = []
        for start in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[start : start + self.MAX_BATCH_SIZE]
            vectors = await self._embed_single_batch(client, batch)
            all_vectors.extend(vectors)

        return all_vectors

    async def _embed_single_batch(
        self, client: AsyncOpenAI, batch: list[str]
    ) -> list[list[float]]:
        """Embed one batch of texts, retrying once on transient failures.

        Args:
            client: The configured OpenAI async client.
            batch: The batch of texts to embed (at most `MAX_BATCH_SIZE`).

        Returns:
            The batch's embedding vectors, in order.

        Raises:
            EmbeddingServiceNotConfiguredError: If the API key is
                rejected as invalid.
            EmbeddingRequestFailedError: If the request fails on both
                the initial attempt and the single retry.
            InvalidEmbeddingDimensionError: If any returned embedding
                does not have `EMBEDDING_DIMENSIONS` dimensions.
        """
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                response = await client.embeddings.create(
                    model=self.MODEL, input=batch
                )
                vectors = [item.embedding for item in response.data]
                for vector in vectors:
                    if len(vector) != EMBEDDING_DIMENSIONS:
                        raise InvalidEmbeddingDimensionError(
                            f"Expected an embedding with "
                            f"{EMBEDDING_DIMENSIONS} dimensions, got "
                            f"{len(vector)}."
                        )
                return vectors
            except AuthenticationError as exc:
                raise EmbeddingServiceNotConfiguredError(
                    "OpenAI rejected the configured API key as invalid."
                ) from exc
            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                last_error = exc
                logger.warning(
                    "Embeddings request failed (attempt %d/2): %s",
                    attempt + 1,
                    exc,
                )
                if attempt == 0:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)

        raise EmbeddingRequestFailedError(
            f"Embeddings request failed after retry: {last_error}"
        ) from last_error


_default_provider = OpenAIEmbeddingProvider()


class EmbeddingService:
    """Entry point for generating embeddings, delegating to a provider."""

    @staticmethod
    async def embed_texts(
        texts: list[str], provider: EmbeddingProvider | None = None
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: The texts to embed, in order.
            provider: The embedding provider to use. Defaults to
                `OpenAIEmbeddingProvider`. Accepting this as a parameter
                is what allows a future embedding backend to be
                substituted with no change to callers.

        Returns:
            A list of embedding vectors, in the same order as `texts`.
        """
        provider = provider or _default_provider
        return await provider.embed_batch(texts)