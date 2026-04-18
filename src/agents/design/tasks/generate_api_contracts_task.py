"""GenerateAPIContractsTask: uses APIContractSkill with workflow validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.design.skills.api_contract_skill import (
    APIContractInput,
    APIContractSkill,
)


class GenerateAPIContractsInput(BaseModel):
    structured_requirements: dict[str, Any]


class APIContractsOutput(BaseModel):
    api_specification: dict[str, Any] = Field(default_factory=dict)


class GenerateAPIContractsTask(BaseTask[GenerateAPIContractsInput, APIContractsOutput]):
    """Generates complete API specification ensuring workflow coverage."""

    name = "generate_api_contracts"
    description = "Generate complete API specification with endpoints covering all user workflows"
    input_schema = GenerateAPIContractsInput
    output_schema = APIContractsOutput
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm
        self._skill = APIContractSkill(llm=llm)

    def get_required_skills(self) -> list[str]:
        return ["api_contract"]

    async def execute(self, input_data: GenerateAPIContractsInput, *, llm: Any | None = None) -> APIContractsOutput:
        reqs = input_data.structured_requirements
        all_rules: list[dict] = []
        for rules in reqs.get("business_rules_by_domain", {}).values():
            all_rules.extend(rules)

        auth_reqs = reqs.get("security_requirements", [])
        roles = reqs.get("user_roles", [])
        if roles:
            auth_reqs.append(f"Roles: {', '.join(r.get('entity_name', r.get('name', '')) for r in roles)}")

        skill_input = APIContractInput(
            entities=reqs.get("entities", []),
            user_workflows=reqs.get("user_workflows", []),
            business_rules=all_rules,
            auth_requirements=auth_reqs,
        )
        result = await self._skill.run(skill_input)
        return APIContractsOutput(api_specification=result.model_dump(mode="json"))
