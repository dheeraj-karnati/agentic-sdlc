"""ComponentDesignSkill: generates frontend component architecture."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class RouteSpec(BaseModel):
    path: str = ""
    page_component: str = ""
    layout: str = ""
    auth_required: bool = True
    required_roles: list[str] = Field(default_factory=list)


class ComponentSpec(BaseModel):
    name: str = ""
    type: str = ""  # page, layout, container, presentational, form, modal, widget
    description: str = ""
    props: list[dict[str, str]] = Field(default_factory=list)  # {name, type, required, description}
    state: list[dict[str, str]] = Field(default_factory=list)  # {name, type, scope}
    api_calls: list[str] = Field(default_factory=list)  # API endpoints this component uses
    children: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)  # events emitted


class FormSpec(BaseModel):
    name: str = ""
    fields: list[dict[str, Any]] = Field(default_factory=list)  # {name, type, validation, label}
    submit_endpoint: str = ""
    validation_rules: list[str] = Field(default_factory=list)
    error_messages: dict[str, str] = Field(default_factory=dict)


class ComponentDesignInput(BaseModel):
    user_workflows: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    api_endpoints: list[dict[str, Any]] = Field(default_factory=list)
    business_rules: list[dict[str, Any]] = Field(default_factory=list)


class ComponentArchitecture(BaseModel):
    framework: str = ""  # Next.js, React, Vue, etc.
    routes: list[RouteSpec] = Field(default_factory=list)
    pages: list[ComponentSpec] = Field(default_factory=list)
    shared_components: list[ComponentSpec] = Field(default_factory=list)
    forms: list[FormSpec] = Field(default_factory=list)
    state_management: str = ""  # approach description
    data_fetching: str = ""  # SWR, React Query, etc.
    component_tree_mermaid: str = ""


_SYSTEM_PROMPT = """\
You are a senior frontend architect designing a component architecture.

Design a complete frontend component system based on the user workflows, entities, \
and API endpoints provided.

Requirements:
- Route hierarchy matching all user workflows
- Component tree: pages → containers → presentational components
- Shared/reusable components (DataTable, FormField, Modal, etc.)
- State management: what state is local vs global, which library
- Forms with validation rules derived from business rules
- Each API endpoint should be consumed by at least one component
- Data fetching strategy (React Query/SWR with caching)

Return JSON matching the output schema."""


class ComponentDesignSkill(BaseSkill[ComponentDesignInput, ComponentArchitecture]):
    """Generates frontend component architecture from workflows and API design."""

    name = "component_design"
    description = "Design frontend component architecture with routes, state, forms, and data fetching"
    input_model = ComponentDesignInput
    output_model = ComponentArchitecture

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: ComponentDesignInput) -> ComponentArchitecture:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(ComponentArchitecture.model_json_schema(), indent=2)
        system = f"{_SYSTEM_PROMPT}\n\nOutput schema:\n```json\n{schema_json}\n```"

        user_content = (
            f"## User Workflows\n{json.dumps(input_data.user_workflows[:10], indent=2, default=str)}"
            f"\n\n## Entities\n{json.dumps(input_data.entities[:20], indent=2, default=str)}"
            f"\n\n## API Endpoints\n{json.dumps(input_data.api_endpoints[:30], indent=2, default=str)}"
            f"\n\n## Business Rules (UI-relevant)\n{json.dumps(input_data.business_rules[:15], indent=2, default=str)}"
        )

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return ComponentArchitecture.model_validate(parsed)
