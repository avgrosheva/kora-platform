"""Shared configuration constants for the RAG (retrieval) infrastructure.

Kept in a small, dependency-free module so both `DocumentEmbedding` (the
ORM model) and `embedding_service.py`/`chunking_service.py` can import
the same values without creating a circular import between the model
and service layers.
"""

EMBEDDING_DIMENSIONS = 1536
"""Vector dimensionality for OpenAI's `text-embedding-3-small` model.

If the embedding model is ever changed to one with a different output
dimensionality, this constant must be updated and a migration run to
alter the `document_embeddings.embedding` column's dimension — pgvector
enforces a fixed dimension per column.
"""

DEFAULT_CHUNK_SIZE_CHARS = 1000
"""Default chunk size, in characters, used by `ChunkingService`."""

DEFAULT_CHUNK_OVERLAP_CHARS = 200
"""Default overlap between consecutive chunks, in characters."""