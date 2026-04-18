"""TextChunkingSkill: splits long text into chunks for processing."""

from __future__ import annotations

import hashlib

import tiktoken
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill


class TextChunk(BaseModel):
    chunk_id: str = ""
    text: str = ""
    token_count: int = 0
    source_section: str = ""
    preceding_context: str = ""


class TextChunkingInput(BaseModel):
    long_text: str
    chunk_strategy: str = "paragraph"  # semantic, fixed, paragraph
    max_tokens_per_chunk: int = 4000
    overlap_tokens: int = 200
    source_id: str = ""


class TextChunkingOutput(BaseModel):
    chunks: list[TextChunk] = Field(default_factory=list)
    total_tokens: int = 0
    chunk_count: int = 0


class TextChunkingSkill(BaseSkill[TextChunkingInput, TextChunkingOutput]):
    """Splits long text into manageable chunks with overlap."""

    name = "text_chunking"
    description = "Split long text into chunks with configurable strategy and overlap"
    input_model = TextChunkingInput
    output_model = TextChunkingOutput

    async def execute(self, input_data: TextChunkingInput) -> TextChunkingOutput:
        if input_data.chunk_strategy == "paragraph":
            return self._chunk_by_paragraph(input_data)
        elif input_data.chunk_strategy == "fixed":
            return self._chunk_by_tokens(input_data)
        else:  # semantic — fall back to paragraph for now
            return self._chunk_by_paragraph(input_data)

    def _chunk_by_paragraph(self, input_data: TextChunkingInput) -> TextChunkingOutput:
        encoder = tiktoken.get_encoding("cl100k_base")
        paragraphs = input_data.long_text.split("\n\n")
        chunks: list[TextChunk] = []
        current_text = ""
        current_tokens = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_tokens = len(encoder.encode(para))

            if current_tokens + para_tokens > input_data.max_tokens_per_chunk and current_text:
                chunks.append(self._make_chunk(
                    current_text, current_tokens, input_data.source_id, len(chunks),
                    preceding_context=chunks[-1].text[-200:] if chunks else "",
                ))
                current_text = ""
                current_tokens = 0

            current_text += ("\n\n" if current_text else "") + para
            current_tokens += para_tokens

        if current_text:
            chunks.append(self._make_chunk(
                current_text, current_tokens, input_data.source_id, len(chunks),
                preceding_context=chunks[-1].text[-200:] if chunks else "",
            ))

        total_tokens = sum(c.token_count for c in chunks)
        return TextChunkingOutput(chunks=chunks, total_tokens=total_tokens, chunk_count=len(chunks))

    def _chunk_by_tokens(self, input_data: TextChunkingInput) -> TextChunkingOutput:
        encoder = tiktoken.get_encoding("cl100k_base")
        tokens = encoder.encode(input_data.long_text)
        chunks: list[TextChunk] = []
        start = 0

        while start < len(tokens):
            end = start + input_data.max_tokens_per_chunk
            chunk_tokens = tokens[start:end]
            text = encoder.decode(chunk_tokens)
            chunks.append(self._make_chunk(
                text, len(chunk_tokens), input_data.source_id, len(chunks),
                preceding_context=chunks[-1].text[-200:] if chunks else "",
            ))
            start += input_data.max_tokens_per_chunk - input_data.overlap_tokens

        total_tokens = sum(c.token_count for c in chunks)
        return TextChunkingOutput(chunks=chunks, total_tokens=total_tokens, chunk_count=len(chunks))

    @staticmethod
    def _make_chunk(
        text: str, token_count: int, source_id: str, index: int, preceding_context: str = ""
    ) -> TextChunk:
        chunk_id = hashlib.md5(f"{source_id}:{index}".encode()).hexdigest()[:12]
        return TextChunk(
            chunk_id=f"chunk_{chunk_id}",
            text=text,
            token_count=token_count,
            source_section=f"chunk_{index}",
            preceding_context=preceding_context,
        )
