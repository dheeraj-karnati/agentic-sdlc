"""QualityAndCompletenessTask: assesses digitized input quality."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.ingest.tasks.generate_source_inventory_task import SourceInventory


class QualityAndCompletenessInput(BaseModel):
    source_inventory: SourceInventory


class DigitizeQualityReport(BaseModel):
    total_content_volume: int = 0  # total words
    format_diversity: int = 0  # number of distinct content types
    processing_quality: float = 0.0  # average quality score
    critical_gaps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    overall_score: float = 0.0
    passing: bool = False


class QualityAndCompletenessTask(BaseTask[QualityAndCompletenessInput, DigitizeQualityReport]):
    """Assesses quality and completeness of digitized inputs."""

    name = "quality_and_completeness"
    description = "Assess digitized input quality, identify gaps, generate warnings"
    input_schema = QualityAndCompletenessInput
    output_schema = DigitizeQualityReport
    prompt_template = ""
    few_shot_examples = []

    def get_required_skills(self) -> list[str]:
        return []

    async def execute(self, input_data: QualityAndCompletenessInput, *, llm: Any | None = None) -> DigitizeQualityReport:
        """Pure computation — no LLM needed."""
        inv = input_data.source_inventory
        gaps: list[str] = []
        warnings: list[str] = []

        # Check for critical gaps
        types = inv.content_type_distribution
        if not types:
            gaps.append("No content was successfully parsed")
        if inv.total_words < 500:
            gaps.append(f"Very low content volume ({inv.total_words} words) — may be insufficient for analysis")
        if inv.is_legacy_modernization and "source_code" not in types:
            warnings.append("Legacy modernization detected but no source code found")
        if not any(t in types for t in ("brd", "srs", "prd", "technical_spec")):
            warnings.append("No formal requirements documents found — Discovery may produce shallow results")

        # Warnings
        if inv.total_sources == 1:
            warnings.append("Only one source file — cross-referencing and conflict detection will be limited")
        for entry in inv.entries:
            if entry.quality_score < 0.3:
                warnings.append(f"Low quality parse for '{entry.original_filename}' — may need manual review")

        # Score
        format_diversity = len(types)
        avg_quality = sum(e.quality_score for e in inv.entries) / max(len(inv.entries), 1)

        volume_score = min(inv.total_words / 5000, 1.0) * 30
        diversity_score = min(format_diversity / 3, 1.0) * 20
        quality_score = avg_quality * 30
        gap_penalty = len(gaps) * 10 + len(warnings) * 3

        overall = max(0, volume_score + diversity_score + quality_score + 20 - gap_penalty)
        overall = min(overall, 100)

        return DigitizeQualityReport(
            total_content_volume=inv.total_words,
            format_diversity=format_diversity,
            processing_quality=round(avg_quality, 2),
            critical_gaps=gaps,
            warnings=warnings,
            overall_score=round(overall, 1),
            passing=overall >= 50 and len(gaps) == 0,
        )
