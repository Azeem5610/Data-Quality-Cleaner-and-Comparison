"""Persistent Chroma storage for raw and cleaned source chunks."""

from functools import lru_cache
from pathlib import Path
import re

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from src.config import CHROMA_DIR, EMBEDDING_MODEL
from src.rag.chunker import TextChunk, chunk_text

BATCH_SIZE = 256
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
    "did", "do", "does", "for", "from", "had", "has", "have", "how",
    "i", "in", "into", "is", "it", "its", "of", "on", "or", "that",
    "the", "their", "them", "there", "this", "to", "was", "were", "what",
    "when", "where", "which", "who", "why", "will", "with",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w]+", text.casefold())
        if len(token) > 1 and token not in _STOP_WORDS
    }


@lru_cache(maxsize=1)
def _client() -> chromadb.PersistentClient:
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


@lru_cache(maxsize=1)
def _embedding_function() -> SentenceTransformerEmbeddingFunction:
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def collection_name(source_id: str, side: str) -> str:
    """Build the stable Chroma collection name for one side of a source."""
    if side not in {"raw", "clean"}:
        raise ValueError("Collection side must be 'raw' or 'clean'.")
    if not source_id or not source_id.isalnum():
        raise ValueError("source_id must contain only letters and numbers.")
    return f"{side}-{source_id.lower()}"


def _collection_metadata(
    source_id: str, side: str, chunks: list[TextChunk], start_index: int = 0
) -> list[dict[str, str | int]]:
    return [
        {
            "source_id": source_id,
            "side": side,
            "chunk_index": start_index + index,
            "start": chunk.start,
            "end": chunk.end,
        }
        for index, chunk in enumerate(chunks)
    ]


def _add_chunks(
    source_id: str,
    side: str,
    text: str,
) -> None:
    chunks = chunk_text(text)
    collection = _client().get_or_create_collection(
        name=collection_name(source_id, side),
        embedding_function=_embedding_function(),
        metadata={"source_id": source_id, "side": side},
    )
    if not chunks:
        return

    for offset in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[offset : offset + BATCH_SIZE]
        collection.add(
            ids=[
                f"{source_id}-{side}-{offset + index}"
                for index in range(len(batch))
            ],
            documents=[chunk.text for chunk in batch],
            metadatas=_collection_metadata(source_id, side, batch, offset),
        )


def index_source(source_id: str, raw_text: str, clean_text: str) -> None:
    """Create the raw and clean collections and add each source's chunks.

    If indexing fails, remove the partially created pair so a source cannot be
    left looking complete when only one side was successfully indexed.
    """
    client = _client()
    names = [collection_name(source_id, side) for side in ("raw", "clean")]
    try:
        _add_chunks(source_id, "raw", raw_text)
        _add_chunks(source_id, "clean", clean_text)
    except Exception:
        for name in names:
            try:
                client.delete_collection(name=name)
            except Exception:
                pass
        raise


def retrieve_chunks(source_id: str, side: str, question: str, top_k: int) -> list[dict]:
    """Return the nearest chunks for one source side, including source offsets."""
    name = collection_name(source_id, side)
    client = _client()
    existing_names = {
        getattr(collection, "name", collection)
        for collection in client.list_collections()
    }
    if name not in existing_names:
        raise KeyError(source_id)

    collection = client.get_collection(
        name=name,
        embedding_function=_embedding_function(),
    )
    count = collection.count()
    if count == 0:
        return []

    # Dense similarity handles paraphrases, but can miss a passage that repeats
    # the question's exact terms. Keep a small semantic candidate set, then
    # blend it with a lexical ranking over the source's chunks.
    dense_result = collection.query(
        query_texts=[question],
        n_results=min(max(1, top_k * 3), count),
        include=["documents", "metadatas"],
    )

    # Chroma's local get is inexpensive for our bounded source size and avoids
    # case-sensitive document filters, which can silently omit valid matches.
    all_result = collection.get(include=["documents", "metadatas"])
    all_documents = all_result.get("documents") or []
    all_metadatas = all_result.get("metadatas") or []
    dense_documents = (dense_result.get("documents") or [[]])[0] or []
    dense_metadatas = (dense_result.get("metadatas") or [[]])[0] or []

    records: dict[int, dict] = {}
    for rank, (document, metadata) in enumerate(
        zip(dense_documents, dense_metadatas), start=1
    ):
        metadata = metadata or {}
        index = int(metadata.get("chunk_index", 0))
        records[index] = {
            "text": document or "",
            "chunk_index": index,
            "start": int(metadata.get("start", 0)),
            "end": int(metadata.get("end", 0)),
            "dense_rank": rank,
        }

    query_tokens = _tokens(question)
    if query_tokens:
        token_sets = [_tokens(document or "") for document in all_documents]
        frequencies = {
            token: sum(token in tokens for tokens in token_sets)
            for token in query_tokens
        }
        weights = {
            token: 1.0 + (count - frequencies[token] + 0.0) / count
            for token in query_tokens
        }
        total_weight = sum(weights.values())
        lexical: list[tuple[float, dict]] = []
        for document, metadata, document_tokens in zip(
            all_documents, all_metadatas, token_sets
        ):
            metadata = metadata or {}
            index = int(metadata.get("chunk_index", 0))
            matched_weight = sum(
                weights[token] for token in query_tokens if token in document_tokens
            )
            if matched_weight:
                lexical_score = matched_weight / total_weight
                lexical.append((lexical_score, {
                    "text": document or "",
                    "chunk_index": index,
                    "start": int(metadata.get("start", 0)),
                    "end": int(metadata.get("end", 0)),
                }))

        lexical.sort(key=lambda item: item[0], reverse=True)
        for lexical_score, record in lexical[: max(top_k * 3, 1)]:
            index = record["chunk_index"]
            existing = records.get(index, record)
            dense_rank = existing.get("dense_rank", count + 1)
            # Exact term coverage can rescue a passage missed by embeddings;
            # semantic rank still contributes for paraphrased questions.
            existing["hybrid_score"] = 0.7 * lexical_score + 0.3 / dense_rank
            records[index] = existing

    if not records:
        return []
    ranked = sorted(
        records.values(),
        key=lambda item: item.get("hybrid_score", 0.3 / item["dense_rank"]),
        reverse=True,
    )
    return [
        {key: value for key, value in record.items() if key not in {"dense_rank", "hybrid_score"}}
        for record in ranked[: max(1, top_k)]
    ]
