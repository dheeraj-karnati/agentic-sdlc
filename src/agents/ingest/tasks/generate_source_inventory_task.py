"""GenerateSourceInventoryTask: creates a complete source inventory for traceability."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.ingest.tasks.classify_and_structure_task import StructuredInputBundle


class SourceEntry(BaseModel):
    source_id: str = ""
    original_filename: str = ""
    content_type: str = ""
    word_count: int = 0
    key_topics: list[str] = Field(default_factory=list)
    quality_score: float = 0.0  # 0-1 based on completeness/parsability
    chunk_count: int = 0


class GenerateSourceInventoryInput(BaseModel):
    structured_bundle: StructuredInputBundle


class SourceInventory(BaseModel):
    entries: list[SourceEntry] = Field(default_factory=list)
    total_sources: int = 0
    total_words: int = 0
    content_type_distribution: dict[str, int] = Field(default_factory=dict)
    is_legacy_modernization: bool = False


class GenerateSourceInventoryTask(BaseTask[GenerateSourceInventoryInput, SourceInventory]):
    """Creates a complete inventory of all digitized sources for traceability."""

    name = "generate_source_inventory"
    description = "Create complete source inventory with quality assessment for pipeline traceability"
    input_schema = GenerateSourceInventoryInput
    output_schema = SourceInventory
    prompt_template = ""
    few_shot_examples = []

    def get_required_skills(self) -> list[str]:
        return []

    async def execute(self, input_data: GenerateSourceInventoryInput, *, llm: Any | None = None) -> SourceInventory:
        """Pure computation — no LLM needed."""
        bundle = input_data.structured_bundle
        entries: list[SourceEntry] = []
        type_dist: dict[str, int] = {}
        total_words = 0

        for src in bundle.sources:
            word_count = len(src.text.split()) if src.text else 0
            total_words += word_count

            # Quality heuristic
            quality = 0.0
            if word_count > 100:
                quality += 0.3
            if word_count > 500:
                quality += 0.2
            if src.confidence > 0.5:
                quality += 0.2
            if src.key_topics:
                quality += 0.15
            if src.content_type != "unknown":
                quality += 0.15

            entries.append(SourceEntry(
                source_id=src.source_id,
                original_filename=src.original_filename,
                content_type=src.content_type,
                word_count=word_count,
                key_topics=src.key_topics,
                quality_score=min(quality, 1.0),
                chunk_count=len(src.chunks),
            ))

            type_dist[src.content_type] = type_dist.get(src.content_type, 0) + 1

        return SourceInventory(
            entries=entries,
            total_sources=len(entries),
            total_words=total_words,
            content_type_distribution=type_dist,
            is_legacy_modernization=bundle.is_legacy_modernization,
        )
