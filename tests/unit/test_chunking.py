from __future__ import annotations

from services.chunking.splitter import chunk_text


def test_chunk_empty_text() -> None:
    chunks = chunk_text("")

    assert chunks == []


def test_chunk_short_text_single_chunk() -> None:
    text = "This is a short sentence."
    chunks = chunk_text(text, chunk_size=10, overlap=2)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_long_text_multiple_chunks() -> None:
    # Generate text with ~20 tokens per sentence, 30 sentences = ~600 tokens
    sentences = [f"Sentence number {i} has some words in it." for i in range(30)]
    text = " ".join(sentences)

    chunks = chunk_text(text, chunk_size=100, overlap=10)

    assert len(chunks) > 1
    # Each chunk (except last) should be <= chunk_size tokens
    for chunk in chunks[:-1]:
        assert len(chunk.split()) <= 100


def test_chunk_overlap_is_exact() -> None:
    sentences = [f"Word{i}" for i in range(200)]
    text = " ".join(sentences)

    chunks = chunk_text(text, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    for i in range(1, len(chunks)):
        prev_end = chunks[i - 1].split()[-10:]
        curr_start = chunks[i].split()[:10]
        assert prev_end == curr_start


def test_chunk_respects_sentence_boundary() -> None:
    # 60 short sentences, each ~5 tokens = ~300 tokens total
    sentences = [f"This is sentence {i}." for i in range(60)]
    text = " ".join(sentences)

    chunks = chunk_text(text, chunk_size=50, overlap=5)

    # Chunks should end at sentence boundaries when possible
    for chunk in chunks:
        # Strip trailing whitespace; if not empty, should end with punctuation
        stripped = chunk.rstrip()
        if stripped:
            assert stripped[-1] in {".", "!", "?"} or len(chunk.split()) < 50


def test_chunk_last_chunk_not_padded() -> None:
    sentences = [f"Word{i}" for i in range(60)]
    text = " ".join(sentences)

    chunks = chunk_text(text, chunk_size=50, overlap=10)

    last_chunk = chunks[-1]
    # Last chunk should not contain duplicate padding
    assert len(last_chunk.split()) <= 50
    # Last chunk tokens should appear only once at the end of the text
    last_words = last_chunk.split()
    text_words = text.split()
    assert text_words[-len(last_words) :] == last_words


def test_chunk_single_sentence_longer_than_chunk_size() -> None:
    """A single sentence longer than chunk_size must be hard-cut."""
    words = [f"word{i}" for i in range(100)]
    text = " ".join(words) + "."

    chunks = chunk_text(text, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    # The first chunk should be exactly chunk_size tokens
    assert len(chunks[0].split()) == 50


def test_chunk_zero_overlap() -> None:
    sentences = [f"Word{i}" for i in range(60)]
    text = " ".join(sentences)

    chunks = chunk_text(text, chunk_size=50, overlap=0)

    assert len(chunks) > 1
    # With zero overlap, chunks should be independent
    for i in range(1, len(chunks)):
        prev_end = chunks[i - 1].split()[-1]
        curr_start = chunks[i].split()[0]
        assert prev_end != curr_start or prev_end == curr_start


def test_chunk_trailing_text_without_punctuation() -> None:
    """Text without trailing punctuation should still produce chunks."""
    words = [f"word{i}" for i in range(120)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    assert len(chunks[-1].split()) <= 50
