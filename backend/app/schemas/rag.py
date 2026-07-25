"""Pydantic schemas for the RAG (retrieval) infrastructure."""

import uuid

from pydantic import BaseModel, Field


class IndexResponse(BaseModel):
    """Response returned after indexing (or reindexing) a document.

    Attributes:
        document_id: The id of the indexed document.
        chunks_indexed: The number of chunks written for this document.
            Reflects the *current* index state — since reindexing
            replaces all prior chunks, this is not cumulative.
    """

    document_id: uuid.UUID
    chunks_indexed: int


class SearchResultRead(BaseModel):
    """A single semantic search result.

    Attributes:
        document_id: The id of the document this chunk belongs to.
        chunk_index: The chunk's position within its source document.
        text: The matching chunk's text content.
        similarity_score: Cosine similarity to the query, in `[-1, 1]`
            (in practice `[0, 1]` for normalized text embeddings), where
            higher means more similar.
    """

    document_id: uuid.UUID
    chunk_index: int
    text: str
    similarity_score: float


class SearchResponse(BaseModel):
    """Response for `GET /search`.

    Attributes:
        query: The original search query text.
        top_k: The maximum number of results requested.
        results: The matching chunks, ordered by similarity, highest
            first.
        total: The number of results actually returned (may be less
            than `top_k` if fewer matches exist).
    """

    query: str
    top_k: int = Field(ge=1, le=50)
    results: list[SearchResultRead]
    total: int