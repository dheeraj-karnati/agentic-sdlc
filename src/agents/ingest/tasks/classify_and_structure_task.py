"""ClassifyAndStructureTask: classifies parsed content and chunks long documents."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.ingest.skills.content_classifier_skill import (
    ContentClassificationInput,
    ContentClassifierSkill,
)
from src.agents.ingest.skills.text_chunking_skill import (
    TextChunkingInput,
    TextChunkingSkill,
)
from src.agents.ingest.tasks.ingest_files_task import IngestedFiles, ParsedInput


class ClassifiedSource(BaseModel):
    source_id: str = ""
    original_filename: str = ""
    input_type: str = ""
    content_type: str = ""  # brd, srs, meeting_notes, source_code, schema, etc.
    language: str = "en"
    domain: str = ""
    key_topics: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    text: str = ""
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    parsed_data: dict[str, Any] = Field(default_factory=dict)


class ClassifyAndStructureInput(BaseModel):
    ingested_files: IngestedFiles


class StructuredInputBundle(BaseModel):
    sources: list[ClassifiedSource] = Field(default_factory=list)
    is_legacy_modernization: bool = False
    has_source_code: bool = False
    has_requirements: bool = False
    total_sources: int = 0


class ClassifyAndStructureTask(BaseTask[ClassifyAndStructureInput, StructuredInputBundle]):
    """Classifies each parsed input and chunks long documents."""

    name = "classify_and_structure"
    description = "Classify content types and chunk long documents for downstream processing"
    input_schema = ClassifyAndStructureInput
    output_schema = StructuredInputBundle
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._classifier = ContentClassifierSkill(llm=llm)
        self._chunker = TextChunkingSkill()

    def get_required_skills(self) -> list[str]:
        return ["content_classifier", "text_chunking"]

    async def execute(self, input_data: ClassifyAndStructureInput, *, llm: Any | None = None) -> StructuredInputBundle:
        sources: list[ClassifiedSource] = []
        has_code = False
        has_reqs = False

        for item in input_data.ingested_files.items:
            # Classify content
            if item.input_type == "code":
                content_type = "source_code"
                classification_result = None
            elif item.parsed_text:
                classification_result = await self._classifier.run(
                    ContentClassificationInput(
                        raw_text=item.parsed_text[:3000],
                        source_filename=item.original_filename,
                    )
                )
                content_type = classification_result.content_type
            else:
                content_type = "unknown"
                classification_result = None

            # Chunk long documents
            chunks: list[dict[str, Any]] = []
            if item.parsed_text and len(item.parsed_text) > 8000:
                chunk_result = await self._chunker.run(
                    TextChunkingInput(
                        long_text=item.parsed_text,
                        chunk_strategy="paragraph",
                        source_id=item.source_id,
                    )
                )
                chunks = [c.model_dump(mode="json") for c in chunk_result.chunks]

            source = ClassifiedSource(
                source_id=item.source_id,
                original_filename=item.original_filename,
                input_type=item.input_type,
                content_type=content_type,
                language=classification_result.language if classification_result else "en",
                domain=classification_result.domain if classification_result else "",
                key_topics=classification_result.key_topics if classification_result else [],
                confidence=classification_result.confidence if classification_result else 0.0,
                text=item.parsed_text,
                chunks=chunks,
                parsed_data=item.parsed_data,
            )
            sources.append(source)

            if content_type == "source_code":
                has_code = True
            if content_type in ("brd", "srs", "prd", "technical_spec"):
                has_reqs = True

        return StructuredInputBundle(
            sources=sources,
            is_legacy_modernization=has_code,
            has_source_code=has_code,
            has_requirements=has_reqs,
            total_sources=len(sources),
        )
