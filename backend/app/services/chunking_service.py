"""Text chunking for document indexing.

Splits extracted document text into overlapping, ordered chunks
suitable for embedding. Chunking is purely a text-transformation
concern — it has no knowledge of documents, organizations, or
embeddings.
"""

from dataclasses import dataclass

from app.core.rag_config import DEFAULT_CHUNK_OVERLAP_CHARS, DEFAULT_CHUNK_SIZE_CHARS


class ChunkingConfigError(Exception):
    """Raised when chunk size/overlap configuration is invalid."""


@dataclass(frozen=True)
class TextChunk:
    """A single ordered chunk of source text.

    Attributes:
        chunk_index: The chunk's position within the source text,
            starting at 0.
        text: The chunk's text content, stripped of leading/trailing
            whitespace.
    """

    chunk_index: int
    text: str


class ChunkingService:
    """Splits text into overlapping, ordered, non-empty chunks.

    Attributes:
        chunk_size: The maximum number of characters per chunk.
        overlap: The number of characters each chunk overlaps with the
            previous one, used to avoid losing context at chunk
            boundaries.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE_CHARS,
        overlap: int = DEFAULT_CHUNK_OVERLAP_CHARS,
    ) -> None:
        """Initialize the chunking configuration.

        Args:
            chunk_size: The maximum number of characters per chunk.
            overlap: The number of characters of overlap between
                consecutive chunks. Must be strictly less than
                `chunk_size`, or chunking would never advance.

        Raises:
            ChunkingConfigError: If `chunk_size` is not positive, or
                `overlap` is negative or `>= chunk_size`.
        """
        if chunk_size <= 0:
            raise ChunkingConfigError("chunk_size must be a positive integer.")
        if overlap < 0:
            raise ChunkingConfigError("overlap must not be negative.")
        if overlap >= chunk_size:
            raise ChunkingConfigError("overlap must be strictly less than chunk_size.")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[TextChunk]:
        """Split text into ordered, overlapping, non-empty chunks.

        Args:
            text: The source text to split. May be empty or
                whitespace-only, in which case no chunks are produced.

        Returns:
            An ordered list of `TextChunk`. Chunks that would be empty
            or whitespace-only after stripping are omitted, but
            `chunk_index` values still reflect their position in the
            original splitting sequence with gaps closed (i.e. the
            returned list is densely re-indexed from 0).
        """
        if not text or not text.strip():
            return []

        step = self.chunk_size - self.overlap
        raw_chunks: list[str] = []

        start = 0
        text_length = len(text)
        while start < text_length:
            raw_chunks.append(text[start : start + self.chunk_size])
            start += step

        chunks: list[TextChunk] = []
        next_index = 0
        for raw in raw_chunks:
            stripped = raw.strip()
            if not stripped:
                continue
            chunks.append(TextChunk(chunk_index=next_index, text=stripped))
            next_index += 1

        return chunks