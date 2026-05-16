from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SearchResult:
    documantions_id: str
    score: float
    title: str | None = None
    chunk_text: str | None = None
    metadata: dict[str, Any] | None = None


def merge_results(
    bm25_results: list[SearchResult],
    vector_results: list[SearchResult],
    vector_weight: float,
    bm25_weight: float,
) -> list[SearchResult]:
    """Merge BM25 and vector search results into a single ranked list.

    The merge process:
    1. Deduplicates by *documantions_id*.
    2. Combines scores using the formula:
       ``combined = vector_weight * vector_score + bm25_weight * bm25_score``
    3. Sorts by combined score descending, with *documantions_id* as tie-breaker.

    When a document appears in both result sets, fields from the BM25 result
    take precedence (e.g. *title*, *metadata*).
    """
    scores: dict[str, float] = {}
    fields: dict[str, dict[str, Any]] = {}

    for result in bm25_results:
        scores[result.documantions_id] = (
            scores.get(result.documantions_id, 0.0) + bm25_weight * result.score
        )
        fields[result.documantions_id] = {
            "title": result.title,
            "chunk_text": result.chunk_text,
            "metadata": result.metadata,
        }

    for result in vector_results:
        scores[result.documantions_id] = (
            scores.get(result.documantions_id, 0.0) + vector_weight * result.score
        )
        # Only set fields if not already present from BM25
        if result.documantions_id not in fields:
            fields[result.documantions_id] = {
                "title": result.title,
                "chunk_text": result.chunk_text,
                "metadata": result.metadata,
            }

    merged: list[SearchResult] = []
    for documantions_id, total_score in scores.items():
        info = fields[documantions_id]
        merged.append(
            SearchResult(
                documantions_id=documantions_id,
                score=total_score,
                title=info.get("title"),
                chunk_text=info.get("chunk_text"),
                metadata=info.get("metadata"),
            )
        )

    # Sort by score descending, then documantions_id ascending for tie-breaking
    merged.sort(key=lambda r: (-r.score, r.documantions_id))
    return merged
