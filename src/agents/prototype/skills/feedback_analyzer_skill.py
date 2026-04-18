"""FeedbackAnalyzerSkill: analyzes stakeholder feedback on prototypes."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class ActionableChange(BaseModel):
    component: str = ""
    change_type: str = ""  # add, modify, remove
    description: str = ""
    priority: str = "medium"  # high, medium, low


class FeedbackAnalysisInput(BaseModel):
    feedback_text: str
    current_prototype_pages: list[str] = Field(default_factory=list)
    feedback_type: str = "freeform"  # freeform, structured


class FeedbackAnalysis(BaseModel):
    changes: list[ActionableChange] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    impact: list[str] = Field(default_factory=list)  # affected pages/components
    requires_design_change: bool = False
    summary: str = ""


_SYSTEM_PROMPT = """\
You are a product analyst interpreting stakeholder feedback on a prototype.

Analyze the feedback and produce:
- changes: actionable changes with component, change_type (add/modify/remove), \
description, priority
- questions: clarification questions if feedback is ambiguous
- impact: list of affected pages/components
- requires_design_change: true if feedback implies changes to the underlying \
architecture, data model, or API (not just UI tweaks)
- summary: one-sentence summary of the feedback

## Examples

**Vague feedback:** "Make it better"
→ questions: ["Which specific pages or features need improvement?", \
"Are there particular UI elements that feel unprofessional?", \
"Is the issue with visual design, data accuracy, or missing functionality?"]
→ changes: [] (can't act without clarification)

**Specific feedback:** "Add a filter dropdown on the inventory table that \
filters by category and status. Also the product prices should show 2 decimal places."
→ changes: [
    {component: "InventoryTable", change_type: "add", description: "Add filter \
dropdown with category and status options", priority: "high"},
    {component: "InventoryTable", change_type: "modify", description: "Format \
product prices to 2 decimal places", priority: "medium"}
  ]
→ questions: []
→ impact: ["InventoryPage", "InventoryTable"]
→ requires_design_change: false

Return JSON matching the output schema."""


class FeedbackAnalyzerSkill(BaseSkill[FeedbackAnalysisInput, FeedbackAnalysis]):
    """Analyzes stakeholder feedback into actionable changes and questions."""

    name = "feedback_analyzer"
    description = "Analyze prototype feedback into actionable changes, questions, and impact assessment"
    input_model = FeedbackAnalysisInput
    output_model = FeedbackAnalysis

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: FeedbackAnalysisInput) -> FeedbackAnalysis:
        llm = self._llm or get_llm(max_tokens=4096)

        schema_json = json.dumps(FeedbackAnalysis.model_json_schema(), indent=2)
        system = f"{_SYSTEM_PROMPT}\n\nOutput schema:\n```json\n{schema_json}\n```"

        user = (
            f"Feedback: {input_data.feedback_text}\n\n"
            f"Current prototype pages: {input_data.current_prototype_pages}"
        )

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=user),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return FeedbackAnalysis.model_validate(parsed)
