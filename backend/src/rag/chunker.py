"""Character-based text chunking with small overlap for retrieval."""

from dataclasses import dataclass

from src.config import CHUNK_OVERLAP, CHUNK_SIZE


@dataclass(frozen=True)
class TextChunk:
    text: str
    start: int
    end: int


def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[TextChunk]:
    """Split text into bounded chunks, preferring paragraph and line boundaries.

    Chunk offsets refer to the original input text and ends are exclusive. Empty
    and whitespace-only ranges are skipped, while overlap preserves context at
    chunk boundaries.
    """
    if chunk_size <= 0:
        raise ValueError("CHUNK_SIZE must be greater than zero.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be between zero and CHUNK_SIZE - 1.")

    chunks: list[TextChunk] = []
    text_length = len(text)
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length:
            # Keep natural boundaries where possible without creating tiny chunks.
            minimum_boundary = start + max(1, chunk_size // 2)
            boundary = max(
                text.rfind("\n\n", start, end),
                text.rfind("\n", start, end),
                text.rfind(" ", start, end),
            )
            if boundary >= minimum_boundary:
                end = boundary

        chunk_start, chunk_end = start, end
        while chunk_start < chunk_end and text[chunk_start].isspace():
            chunk_start += 1
        while chunk_end > chunk_start and text[chunk_end - 1].isspace():
            chunk_end -= 1
        if chunk_start < chunk_end:
            chunks.append(TextChunk(text[chunk_start:chunk_end], chunk_start, chunk_end))

        if end >= text_length:
            break
        next_start = end - overlap
        # Ensure progress even for pathological boundaries or a large overlap.
        start = max(start + 1, next_start)

    return chunks
