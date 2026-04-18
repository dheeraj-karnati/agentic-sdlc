"""ProcessFeedbackTask: analyzes user feedback and prepares for regeneration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.prototype.skills.feedback_analyzer_skill import (
    FeedbackAnalysisInput,
    FeedbackAnalyzerSkill,
)


class ProcessFeedbackInput(BaseModel):
    feedback_text: str
    current_pages: list[str] = Field(default_factory=list)
    existing_feedback_history: list[dict[str, Any]] = Field(default_factory=list)


class ProcessFeedbackOutput(BaseModel):
    analysis: dict[str, Any] = Field(default_factory=dict)
    updated_feedback_history: list[dict[str, Any]] = Field(default_factory=list)
    has_questions: bool = False
    requires_design_change: bool = False


class ProcessFeedbackTask(BaseTask[ProcessFeedbackInput, ProcessFeedbackOutput]):
    """Analyzes feedback and appends to feedback history for regeneration."""

    name = "process_feedback"
    description = "Analyze stakeholder feedback, produce actionable changes, update feedback history"
    input_schema = ProcessFeedbackInput
    output_schema = ProcessFeedbackOutput
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._skill = FeedbackAnalyzerSkill(llm=llm)

    def get_required_skills(self) -> list[str]:
        return ["feedback_analyzer"]

    async def execute(self, input_data: ProcessFeedbackInput, *, llm: Any | None = None) -> ProcessFeedbackOutput:
        result = await self._skill.run(
            FeedbackAnalysisInput(
                feedback_text=input_data.feedback_text,
                current_prototype_pages=input_data.current_pages,
            )
        )

        analysis = result.model_dump(mode="json")

        # Append to feedback history
        updated_history = list(input_data.existing_feedback_history) + [{
            "round": len(input_data.existing_feedback_history) + 1,
            "raw_feedback": input_data.feedback_text,
            "changes": analysis.get("changes", []),
            "summary": analysis.get("summary", ""),
        }]

        return ProcessFeedbackOutput(
            analysis=analysis,
            updated_feedback_history=updated_history,
            has_questions=len(result.questions) > 0,
            requires_design_change=result.requires_design_change,
        )
