"""Token-based text chunking with sentence-boundary awareness."""

from __future__ import annotations

import re

# Sentence boundary pattern: punctuation followed by space and capital letter or end of string
_SENTENCE_PATTERN = re.compile(r"[.!?]\s+(?=[A-Z])|[.!?]\s*$")


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split *text* into chunks of at most *chunk_size* tokens (whitespace-split).

    Chunks are split on sentence boundaries when possible. When a sentence
    would exceed the remaining token budget, a hard cut is made at the token
    limit. *overlap* tokens from the end of the previous chunk are repeated at
    the start of the next chunk. The last chunk is not padded.

    Returns an empty list when *text* is empty or whitespace-only.
    """
    words = text.split()
    if not words:
        return []

    # Split text into sentences
    sentences = _split_sentences(text)
    chunks: list[str] = []
    current_chunk_words: list[str] = []

    for sentence in sentences:
        sentence_words = sentence.split()
        # Check if adding this sentence would exceed chunk_size
        if current_chunk_words and len(current_chunk_words) + len(sentence_words) > chunk_size:
            # Flush current chunk
            chunks.append(" ".join(current_chunk_words))
            # Start new chunk with overlap from previous chunk
            overlap_words = current_chunk_words[-overlap:] if overlap > 0 else []
            current_chunk_words = overlap_words + sentence_words
        else:
            if current_chunk_words:
                current_chunk_words.extend(sentence_words)
            else:
                current_chunk_words = sentence_words[:]

        # If a single sentence is longer than chunk_size, hard-cut it
        while len(current_chunk_words) > chunk_size:
            chunk_words = current_chunk_words[:chunk_size]
            chunks.append(" ".join(chunk_words))
            overlap_words = chunk_words[-overlap:] if overlap > 0 else []
            current_chunk_words = overlap_words + current_chunk_words[chunk_size:]

    # Flush remaining words
    if current_chunk_words:
        chunks.append(" ".join(current_chunk_words))

    return chunks


def _split_sentences(text: str) -> list[str]:
    """Split *text* into sentences, preserving the punctuation at the end."""
    if not text.strip():
        return []

    # Use regex to find sentence boundaries
    matches = list(_SENTENCE_PATTERN.finditer(text))
    if not matches:
        return [text.strip()]

    sentences: list[str] = []
    start = 0
    for match in matches:
        end = match.end()
        sentence = text[start:end].strip()
        if sentence:
            sentences.append(sentence)
        start = end

    # Handle trailing text after last sentence boundary
    if start < len(text):
        trailing = text[start:].strip()
        if trailing:
            sentences.append(trailing)

    return sentences
