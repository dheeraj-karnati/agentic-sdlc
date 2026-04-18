"""Text embedding utilities with automatic provider selection.

Uses OpenAI text-embedding-3-small (1536-dim) when OPENAI_API_KEY is set,
falls back to Ollama nomic-embed-text (768-dim) for local development.
"""

import logging

import tiktoken
from langchain_core.embeddings import Embeddings

from src.config import settings

logger = logging.getLogger(__name__)

MAX_TOKENS_PER_CHUNK = 8000
CHUNK_OVERLAP_TOKENS = 200


def _get_embeddings_client() -> Embeddings:
    """Create an embeddings client, preferring OpenAI and falling back to Ollama."""
    if settings.openai_api_key:
        from langchain_openai import OpenAIEmbeddings

        logger.debug("Using OpenAI for embeddings")
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536,
            openai_api_key=settings.openai_api_key,
        )

    from langchain_ollama import OllamaEmbeddings

    logger.info(
        "OPENAI_API_KEY not set — falling back to Ollama embeddings (%s at %s)",
        settings.ollama_embed_model,
        settings.ollama_base_url,
    )
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )


def get_embedding_dimensions() -> int:
    """Return the embedding dimension for the active provider."""
    if settings.openai_api_key:
        return 1536
    return 768  # nomic-embed-text default


def chunk_text(
    text: str,
    max_tokens: int = MAX_TOKENS_PER_CHUNK,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """Split text into chunks that fit within the token limit.

    Uses tiktoken (cl100k_base) for accurate token counting.
    Chunks overlap by `overlap_tokens` to preserve context across boundaries.
    """
    encoder = tiktoken.get_encoding("cl100k_base")
    tokens = encoder.encode(text)

    if len(tokens) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunks.append(encoder.decode(chunk_tokens))
        start += max_tokens - overlap_tokens

    return chunks


async def embed_text(text: str) -> list[float]:
    """Embed a single text string, returning a vector.

    Dimension depends on the active provider:
    - OpenAI: 1536-dim
    - Ollama (nomic-embed-text): 768-dim

    If the text exceeds the token limit, it is chunked and the
    chunk embeddings are averaged into a single vector.
    """
    client = _get_embeddings_client()
    chunks = chunk_text(text)

    if len(chunks) == 1:
        return await client.aembed_query(chunks[0])

    vectors = await client.aembed_documents(chunks)
    return _average_vectors(vectors)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single batch call."""
    client = _get_embeddings_client()
    return await client.aembed_documents(texts)


def _average_vectors(vectors: list[list[float]]) -> list[float]:
    """Average multiple embedding vectors into one."""
    n = len(vectors)
    dim = len(vectors[0])
    averaged = [0.0] * dim
    for vec in vectors:
        for i in range(dim):
            averaged[i] += vec[i]
    return [v / n for v in averaged]
