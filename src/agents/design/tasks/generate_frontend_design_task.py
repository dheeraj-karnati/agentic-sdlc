"""GenerateFrontendDesignTask: uses ComponentDesignSkill."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.design.skills.component_design_skill import (
    ComponentDesignInput,
    ComponentDesignSkill,
)


class GenerateFrontendDesignInput(BaseModel):
    structured_requirements: dict[str, Any]
    api_specification: dict[str, Any] = Field(default_factory=dict)


class FrontendDesignOutput(BaseModel):
    frontend_components: dict[str, Any] = Field(default_factory=dict)


class GenerateFrontendDesignTask(BaseTask[GenerateFrontendDesignInput, FrontendDesignOutput]):
    """Generates frontend component architecture consuming the API specification."""

    name = "generate_frontend_design"
    description = "Generate frontend component architecture with routes, state, and forms"
    input_schema = GenerateFrontendDesignInput
    output_schema = FrontendDesignOutput
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm
        self._skill = ComponentDesignSkill(llm=llm)

    def get_required_skills(self) -> list[str]:
        return ["component_design"]

    async def execute(self, input_data: GenerateFrontendDesignInput, *, llm: Any | None = None) -> FrontendDesignOutput:
        reqs = input_data.structured_requirements
        api = input_data.api_specification
        all_rules: list[dict] = []
        for rules in reqs.get("business_rules_by_domain", {}).values():
            all_rules.extend(rules)

        endpoints = api.get("endpoints", [])

        skill_input = ComponentDesignInput(
            user_workflows=reqs.get("user_workflows", []),
            entities=reqs.get("entities", []),
            api_endpoints=endpoints,
            business_rules=all_rules,
        )
        result = await self._skill.run(skill_input)
        return FrontendDesignOutput(frontend_components=result.model_dump(mode="json"))
