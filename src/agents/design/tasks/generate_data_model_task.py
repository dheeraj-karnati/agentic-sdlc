"""GenerateDataModelTask: uses SchemaDesignSkill and cross-validates."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.design.skills.schema_design_skill import (
    SchemaDesignInput,
    SchemaDesignSkill,
)


class GenerateDataModelInput(BaseModel):
    structured_requirements: dict[str, Any]


class DataModelOutput(BaseModel):
    database_schema: dict[str, Any] = Field(default_factory=dict)


class GenerateDataModelTask(BaseTask[GenerateDataModelInput, DataModelOutput]):
    """Generates complete database schema and validates against business rules."""

    name = "generate_data_model"
    description = "Generate production database schema ensuring all business rules are implementable"
    input_schema = GenerateDataModelInput
    output_schema = DataModelOutput
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm
        self._skill = SchemaDesignSkill(llm=llm)

    def get_required_skills(self) -> list[str]:
        return ["schema_design"]

    async def execute(self, input_data: GenerateDataModelInput, *, llm: Any | None = None) -> DataModelOutput:
        reqs = input_data.structured_requirements
        all_rules: list[dict] = []
        for rules in reqs.get("business_rules_by_domain", {}).values():
            all_rules.extend(rules)

        skill_input = SchemaDesignInput(
            entities=reqs.get("entities", []),
            business_rules=all_rules,
            database_type="postgresql",
        )
        result = await self._skill.run(skill_input)
        return DataModelOutput(database_schema=result.model_dump(mode="json"))
