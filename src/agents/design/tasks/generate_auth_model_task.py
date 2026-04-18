"""GenerateAuthModelTask: uses AuthDesignSkill with role validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.design.skills.auth_design_skill import (
    AuthDesignInput,
    AuthDesignSkill,
)


class GenerateAuthModelInput(BaseModel):
    structured_requirements: dict[str, Any]


class AuthModelOutput(BaseModel):
    auth_design: dict[str, Any] = Field(default_factory=dict)


class GenerateAuthModelTask(BaseTask[GenerateAuthModelInput, AuthModelOutput]):
    """Generates complete auth design validated against role-related business rules."""

    name = "generate_auth_model"
    description = "Generate complete authentication and authorization design"
    input_schema = GenerateAuthModelInput
    output_schema = AuthModelOutput
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm
        self._skill = AuthDesignSkill(llm=llm)

    def get_required_skills(self) -> list[str]:
        return ["auth_design"]

    async def execute(self, input_data: GenerateAuthModelInput, *, llm: Any | None = None) -> AuthModelOutput:
        reqs = input_data.structured_requirements

        # Extract auth-related business rules
        auth_rules: list[dict] = []
        for domain, rules in reqs.get("business_rules_by_domain", {}).items():
            if domain in ("authentication", "authorization", "security", "access_control"):
                auth_rules.extend(rules)
            else:
                # Include rules that mention roles, permissions, or access
                for rule in rules:
                    desc = str(rule.get("description", "") or rule.get("content", "")).lower()
                    if any(kw in desc for kw in ("role", "permission", "access", "admin", "manager", "auth", "login")):
                        auth_rules.append(rule)

        skill_input = AuthDesignInput(
            user_roles=reqs.get("user_roles", []),
            business_rules=auth_rules,
            security_requirements=reqs.get("security_requirements", []),
        )
        result = await self._skill.run(skill_input)
        return AuthModelOutput(auth_design=result.model_dump(mode="json"))
