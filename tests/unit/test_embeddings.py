"""Unit tests for embedding utilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.embeddings import (
    MAX_TOKENS_PER_CHUNK,
    _average_vectors,
    chunk_text,
    embed_text,
    embed_texts,
    get_embedding_dimensions,
)

EMBEDDING_DIMENSIONS = get_embedding_dimensions()


# ─── chunk_text tests ───


def test_chunk_text_short_text() -> None:
    """Short text returns a single chunk."""
    result = chunk_text("Hello, world!")
    assert result == ["Hello, world!"]


def test_chunk_text_returns_list_of_strings() -> None:
    """All chunks are strings."""
    result = chunk_text("word " * 10000, max_tokens=100, overlap_tokens=10)
    assert all(isinstance(c, str) for c in result)


def test_chunk_text_respects_max_tokens() -> None:
    """Each chunk fits within the token limit."""
    import tiktoken

    encoder = tiktoken.get_encoding("cl100k_base")
    long_text = "word " * 20000
    chunks = chunk_text(long_text, max_tokens=500, overlap_tokens=50)

    assert len(chunks) > 1
    for chunk in chunks:
        token_count = len(encoder.encode(chunk))
        assert token_count <= 500


def test_chunk_text_overlap() -> None:
    """Chunks overlap so that no content is lost at boundaries."""
    import tiktoken

    encoder = tiktoken.get_encoding("cl100k_base")
    long_text = "word " * 5000
    chunks = chunk_text(long_text, max_tokens=200, overlap_tokens=50)

    assert len(chunks) > 2
    # Verify overlap: end of chunk N shares tokens with start of chunk N+1
    for i in range(len(chunks) - 1):
        tokens_current = encoder.encode(chunks[i])
        tokens_next = encoder.encode(chunks[i + 1])
        tail = tokens_current[-50:]
        head = tokens_next[:50]
        assert tail == head


def test_chunk_text_covers_all_content() -> None:
    """Chunking and reassembly preserves all tokens."""
    import tiktoken

    encoder = tiktoken.get_encoding("cl100k_base")
    long_text = "unique_word_" + " another_word" * 3000
    original_tokens = encoder.encode(long_text)

    chunks = chunk_text(long_text, max_tokens=500, overlap_tokens=50)
    # First chunk starts at token 0, last chunk ends at or past the end
    first_tokens = encoder.encode(chunks[0])
    last_tokens = encoder.encode(chunks[-1])
    assert first_tokens[:10] == original_tokens[:10]
    assert last_tokens[-10:] == original_tokens[-10:]


def test_chunk_text_empty_string() -> None:
    """Empty string returns a single-element list."""
    result = chunk_text("")
    assert result == [""]


def test_chunk_text_exact_limit() -> None:
    """Text exactly at the token limit returns one chunk."""
    import tiktoken

    encoder = tiktoken.get_encoding("cl100k_base")
    # Build text that is exactly MAX_TOKENS_PER_CHUNK tokens
    tokens = encoder.encode("a " * 10000)[:MAX_TOKENS_PER_CHUNK]
    text = encoder.decode(tokens)
    result = chunk_text(text)
    assert len(result) == 1


# ─── _average_vectors tests ───


def test_average_vectors_single() -> None:
    """Averaging a single vector returns itself."""
    vec = [1.0, 2.0, 3.0]
    result = _average_vectors([vec])
    assert result == [1.0, 2.0, 3.0]


def test_average_vectors_multiple() -> None:
    """Averaging two vectors gives the element-wise mean."""
    v1 = [1.0, 0.0, 4.0]
    v2 = [3.0, 2.0, 0.0]
    result = _average_vectors([v1, v2])
    assert result == [2.0, 1.0, 2.0]


def test_average_vectors_preserves_dimensions() -> None:
    """Output dimension matches input dimension."""
    vecs = [[float(i) for i in range(EMBEDDING_DIMENSIONS)] for _ in range(3)]
    result = _average_vectors(vecs)
    assert len(result) == EMBEDDING_DIMENSIONS


# ─── embed_text tests ───


@pytest.mark.asyncio
async def test_embed_text_short() -> None:
    """Short text calls aembed_query once and returns the vector."""
    mock_vector = [0.1] * EMBEDDING_DIMENSIONS
    mock_client = MagicMock()
    mock_client.aembed_query = AsyncMock(return_value=mock_vector)

    with patch("src.tools.embeddings._get_embeddings_client", return_value=mock_client):
        result = await embed_text("short text")

    assert result == mock_vector
    mock_client.aembed_query.assert_awaited_once_with("short text")


@pytest.mark.asyncio
async def test_embed_text_long_averages_chunks() -> None:
    """Long text is chunked, each chunk embedded, and vectors averaged."""
    dim = EMBEDDING_DIMENSIONS
    vec1 = [1.0] * dim
    vec2 = [3.0] * dim
    mock_client = MagicMock()
    mock_client.aembed_documents = AsyncMock(return_value=[vec1, vec2])

    fake_chunks = ["chunk1", "chunk2"]
    with (
        patch("src.tools.embeddings._get_embeddings_client", return_value=mock_client),
        patch("src.tools.embeddings.chunk_text", return_value=fake_chunks),
    ):
        result = await embed_text("very long text")

    assert len(result) == dim
    assert result[0] == pytest.approx(2.0)
    mock_client.aembed_documents.assert_awaited_once_with(fake_chunks)


# ─── embed_texts tests ───


@pytest.mark.asyncio
async def test_embed_texts_batch() -> None:
    """embed_texts calls aembed_documents with all texts."""
    dim = EMBEDDING_DIMENSIONS
    mock_vectors = [[0.1] * dim, [0.2] * dim, [0.3] * dim]
    mock_client = MagicMock()
    mock_client.aembed_documents = AsyncMock(return_value=mock_vectors)

    texts = ["text one", "text two", "text three"]
    with patch("src.tools.embeddings._get_embeddings_client", return_value=mock_client):
        result = await embed_texts(texts)

    assert len(result) == 3
    assert result[0] == mock_vectors[0]
    mock_client.aembed_documents.assert_awaited_once_with(texts)