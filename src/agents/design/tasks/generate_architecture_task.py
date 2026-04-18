"""GenerateArchitectureTask: uses ArchitectureDecisionSkill + creates ADRs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.design.skills.architecture_decision_skill import (
    ArchitectureDecisionInput,
    ArchitectureDecisionSkill,
)


class GenerateArchitectureInput(BaseModel):
    structured_requirements: dict[str, Any]


class ArchitectureOutput(BaseModel):
    architecture: dict[str, Any] = Field(default_factory=dict)


class GenerateArchitectureTask(BaseTask[GenerateArchitectureInput, ArchitectureOutput]):
    """Generates architecture recommendation with ADRs via skill dispatch."""

    name = "generate_architecture"
    description = "Generate architecture recommendation with technology stack and ADRs"
    input_schema = GenerateArchitectureInput
    output_schema = ArchitectureOutput
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm
        self._skill = ArchitectureDecisionSkill(llm=llm)

    def get_required_skills(self) -> list[str]:
        return ["architecture_decision"]

    async def execute(self, input_data: GenerateArchitectureInput, *, llm: Any | None = None) -> ArchitectureOutput:
        reqs = input_data.structured_requirements
        skill_input = ArchitectureDecisionInput(
            system_understanding=reqs.get("system_purpose", ""),
            business_rules=self._flatten_rules(reqs.get("business_rules_by_domain", {})),
            entity_list=reqs.get("entities", []),
            constraints=reqs.get("constraints", []),
            non_functional_requirements=reqs.get("non_functional_requirements", []),
        )
        result = await self._skill.run(skill_input)
        return ArchitectureOutput(architecture=result.model_dump(mode="json"))

    @staticmethod
    def _flatten_rules(rules_by_domain: dict[str, list]) -> list[dict]:
        flat: list[dict] = []
        for rules in rules_by_domain.values():
            flat.extend(rules)
        return flat
