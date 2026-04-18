"""ArchitectureDecisionSkill: evaluates and recommends system architecture."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class TechnologyChoice(BaseModel):
    category: str = ""  # backend_framework, frontend_framework, database, cache, message_queue
    technology: str = ""
    justification: str = ""
    alternatives_considered: list[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    risk: str = ""
    likelihood: str = "medium"  # high, medium, low
    impact: str = "medium"
    mitigation: str = ""


class ArchitectureDecisionInput(BaseModel):
    system_understanding: str = ""
    business_rules: list[dict[str, Any]] = Field(default_factory=list)
    entity_list: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)


class ArchitectureDecision(BaseModel):
    pattern: str = ""  # monolith, modular_monolith, microservices
    rationale: str = ""
    trade_offs: list[str] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    recommended_stack: list[TechnologyChoice] = Field(default_factory=list)
    component_diagram: str = ""  # Mermaid diagram
    communication_patterns: str = ""
    deployment_model: str = ""
    adrs: list[dict[str, str]] = Field(default_factory=list)  # Architecture Decision Records


_SYSTEM_PROMPT = """\
You are a principal software architect evaluating architecture options for a \
system modernization project.

Evaluate the system requirements and recommend an architecture pattern. Consider:
- Team size and expertise implications
- Deployment complexity and operational overhead
- Scalability needs from non-functional requirements
- Data consistency requirements from business rules
- Integration complexity with external systems

For the recommended stack, justify EACH technology choice against the requirements.

Return JSON with:
- pattern: "monolith", "modular_monolith", or "microservices"
- rationale: detailed justification (2+ paragraphs)
- trade_offs: list of trade-offs of the chosen pattern
- risks: list of {risk, likelihood, impact, mitigation}
- recommended_stack: list of {category, technology, justification, alternatives_considered}
  Categories: backend_framework, frontend_framework, database, cache, message_queue, \
search_engine, object_storage, monitoring
- component_diagram: Mermaid diagram showing system components
- communication_patterns: how components communicate
- deployment_model: how the system is deployed
- adrs: list of Architecture Decision Records, each with {title, context, decision, \
consequences}"""


class ArchitectureDecisionSkill(
    BaseSkill[ArchitectureDecisionInput, ArchitectureDecision]
):
    """Evaluates requirements and recommends system architecture with full rationale."""

    name = "architecture_decision"
    description = "Evaluate requirements and recommend architecture pattern with technology stack"
    input_model = ArchitectureDecisionInput
    output_model = ArchitectureDecision

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: ArchitectureDecisionInput) -> ArchitectureDecision:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(ArchitectureDecision.model_json_schema(), indent=2)
        system = f"{_SYSTEM_PROMPT}\n\nOutput schema:\n```json\n{schema_json}\n```"

        user_parts = [
            f"## System Understanding\n{input_data.system_understanding}",
            f"\n## Business Rules ({len(input_data.business_rules)} rules)\n"
            + json.dumps(input_data.business_rules[:20], indent=2, default=str),
            f"\n## Domain Entities ({len(input_data.entity_list)} entities)\n"
            + json.dumps(input_data.entity_list[:20], indent=2, default=str),
        ]
        if input_data.constraints:
            user_parts.append("\n## Constraints\n" + "\n".join(f"- {c}" for c in input_data.constraints))
        if input_data.non_functional_requirements:
            user_parts.append("\n## Non-Functional Requirements\n" + "\n".join(f"- {r}" for r in input_data.non_functional_requirements))

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content="\n".join(user_parts)),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return ArchitectureDecision.model_validate(parsed)
