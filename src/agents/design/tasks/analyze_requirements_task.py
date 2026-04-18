"""AnalyzeRequirementsTask: structures Discovery outputs for design decisions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class AnalyzeRequirementsInput(BaseModel):
    business_context: list[dict[str, Any]] = Field(default_factory=list)


class StructuredRequirements(BaseModel):
    system_purpose: str = ""
    business_rules_by_domain: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    user_workflows: list[dict[str, Any]] = Field(default_factory=list)
    user_roles: list[dict[str, Any]] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    security_requirements: list[str] = Field(default_factory=list)
    integration_points: list[dict[str, Any]] = Field(default_factory=list)
    technology_assessment: str = ""


class AnalyzeRequirementsTask(BaseTask[AnalyzeRequirementsInput, StructuredRequirements]):
    """Structures Discovery outputs into organized requirements for design tasks."""

    name = "analyze_requirements"
    description = (
        "Analyze and structure business context from Discovery into organized "
        "requirements grouped by domain area, ready for design decisions"
    )
    input_schema = AnalyzeRequirementsInput
    output_schema = StructuredRequirements

    prompt_template = """\
Analyze the business context entries from the Discovery phase and organize them \
into structured requirements for system design.

Group business rules by domain area (e.g., authentication, orders, inventory, reporting).
Extract user roles with their access levels.
Identify non-functional requirements and constraints.
Extract security-specific requirements.
Identify external integration points.

Business context entries: {business_context}"""

    few_shot_examples = [
        {
            "input": {"business_context": [
                {"category": "business_rule", "title": "Login lockout", "content": "Lock after 3 failed attempts"},
                {"category": "domain_entity", "title": "Order", "content": "Purchase order with total and status"},
            ]},
            "output": {
                "system_purpose": "Inventory management system with order processing",
                "business_rules_by_domain": {
                    "authentication": [{"title": "Login lockout", "description": "Lock after 3 failed attempts"}],
                    "orders": [],
                },
                "entities": [{"entity_name": "Order", "attributes": ["total", "status"]}],
                "user_workflows": [],
                "user_roles": [],
                "non_functional_requirements": [],
                "constraints": [],
                "security_requirements": ["Account lockout after failed login attempts"],
                "integration_points": [],
                "technology_assessment": "",
            },
        },
    ]

    def get_required_skills(self) -> list[str]:
        return []

    def validate(self, output: StructuredRequirements) -> bool:
        return bool(output.business_rules_by_domain or output.entities)
