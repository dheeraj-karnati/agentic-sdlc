"""DesignInterpreterSkill: parses Design artifacts into a PrototypeSpec."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class PageSpec(BaseModel):
    route: str = ""
    title: str = ""
    components: list[str] = Field(default_factory=list)
    layout: str = "default"
    auth_required: bool = True
    required_roles: list[str] = Field(default_factory=list)


class ComponentSpec(BaseModel):
    name: str = ""
    type: str = ""  # page, layout, form, table, card, modal, nav
    props: list[dict[str, str]] = Field(default_factory=list)
    data_source: str = ""  # API endpoint or mock key
    children: list[str] = Field(default_factory=list)


class MockDataModel(BaseModel):
    entity_name: str = ""
    fields: list[dict[str, str]] = Field(default_factory=list)
    sample_count: int = 5
    sample_data: list[dict[str, Any]] = Field(default_factory=list)


class APIMock(BaseModel):
    method: str = ""
    path: str = ""
    response_schema: dict[str, Any] = Field(default_factory=dict)
    sample_response: dict[str, Any] = Field(default_factory=dict)


class AuthConfig(BaseModel):
    roles: list[str] = Field(default_factory=list)
    default_role: str = "viewer"
    login_page: str = "/login"


class NavItem(BaseModel):
    label: str = ""
    route: str = ""
    icon: str = ""
    roles: list[str] = Field(default_factory=list)


class DesignInterpreterInput(BaseModel):
    design_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    business_context: list[dict[str, Any]] = Field(default_factory=list)


class PrototypeSpec(BaseModel):
    pages: list[PageSpec] = Field(default_factory=list)
    components: list[ComponentSpec] = Field(default_factory=list)
    mock_data_models: list[MockDataModel] = Field(default_factory=list)
    api_mocks: list[APIMock] = Field(default_factory=list)
    navigation: list[NavItem] = Field(default_factory=list)
    auth_config: AuthConfig = Field(default_factory=AuthConfig)
    framework: str = "nextjs"
    styling: str = "tailwind + shadcn/ui"


_SYSTEM_PROMPT = """\
You are a senior frontend architect translating Design artifacts into a \
prototype specification.

Parse the design artifacts and produce a PrototypeSpec with:
- pages: routes, titles, components, auth requirements per page
- components: name, type, props, data source, children
- mock_data_models: entity name, fields, realistic sample data (5 records)
- api_mocks: method, path, sample response matching the DB schema
- navigation: sidebar/topbar items with role-based visibility
- auth_config: roles, default role, login page route

Use REALISTIC domain-specific mock data, not lorem ipsum. If the system \
is an inventory app, use product names like "Widget A", "Sensor B" with \
realistic prices and quantities.

Return JSON matching the output schema."""


class DesignInterpreterSkill(BaseSkill[DesignInterpreterInput, PrototypeSpec]):
    """Parses Design artifacts into a structured prototype specification."""

    name = "design_interpreter"
    description = "Parse Design artifacts into pages, components, mock data, and API mocks"
    input_model = DesignInterpreterInput
    output_model = PrototypeSpec

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: DesignInterpreterInput) -> PrototypeSpec:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(PrototypeSpec.model_json_schema(), indent=2)
        system = f"{_SYSTEM_PROMPT}\n\nOutput schema:\n```json\n{schema_json}\n```"

        artifacts_text = json.dumps(input_data.design_artifacts[:10], indent=2, default=str)
        context_text = json.dumps(input_data.business_context[:5], indent=2, default=str)

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=f"## Design Artifacts\n{artifacts_text}\n\n## Business Context\n{context_text}"),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return PrototypeSpec.model_validate(parsed)
