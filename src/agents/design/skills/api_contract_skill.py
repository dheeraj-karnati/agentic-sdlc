"""APIContractSkill: generates complete OpenAPI 3.1 specifications."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class EndpointParam(BaseModel):
    name: str = ""
    location: str = "query"  # query, path, header
    type: str = "string"
    required: bool = False
    description: str = ""


class EndpointSpec(BaseModel):
    method: str = ""  # GET, POST, PUT, PATCH, DELETE
    path: str = ""
    summary: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    auth_required: bool = True
    required_roles: list[str] = Field(default_factory=list)
    parameters: list[EndpointParam] = Field(default_factory=list)
    request_schema: dict[str, Any] = Field(default_factory=dict)
    response_schema: dict[str, Any] = Field(default_factory=dict)
    error_responses: list[dict[str, Any]] = Field(default_factory=list)
    rate_limit: str = ""  # e.g. "100/min"
    business_rules_enforced: list[str] = Field(default_factory=list)


class APIContractInput(BaseModel):
    entities: list[dict[str, Any]] = Field(default_factory=list)
    user_workflows: list[dict[str, Any]] = Field(default_factory=list)
    business_rules: list[dict[str, Any]] = Field(default_factory=list)
    auth_requirements: list[str] = Field(default_factory=list)


class APISpecification(BaseModel):
    base_path: str = "/api/v1"
    endpoints: list[EndpointSpec] = Field(default_factory=list)
    openapi_yaml: str = ""
    pagination_strategy: str = ""
    filtering_strategy: str = ""
    error_format: dict[str, Any] = Field(default_factory=dict)
    rate_limiting: dict[str, Any] = Field(default_factory=dict)


_SYSTEM_PROMPT = """\
You are a senior API architect designing a production REST API (OpenAPI 3.1).

Generate complete API endpoints for the given domain entities and workflows.

Requirements:
- Full CRUD for each data entity (GET list, GET by id, POST, PUT/PATCH, DELETE)
- Domain-specific action endpoints (e.g., POST /orders/{id}/approve)
- Request/response schemas as JSON Schema matching the database schema
- Authentication: specify which endpoints need auth, which roles can access
- Pagination: cursor-based or offset-based with consistent format
- Filtering: query params for list endpoints (status, date range, search)
- Sorting: sortable fields per resource
- Error responses: 400 (validation), 401 (unauth), 403 (forbidden), 404, 409 (conflict), 422, 429, 500
- Rate limiting recommendations per endpoint category
- Every business rule must have an enforcement point in the API

## Example: Basic vs Production API

BAD (basic):
```yaml
GET /products  # list products
POST /products  # create product
```

GOOD (production):
```yaml
GET /api/v1/products?status=active&category=electronics&sort=-created_at&page=1&limit=20
  Auth: Bearer token, roles: [viewer, manager, admin]
  Response: {items: [...], total: 100, page: 1, limit: 20, has_next: true}
  Errors: 401, 403, 500

POST /api/v1/products
  Auth: Bearer token, roles: [manager, admin]
  Body: {name, sku, price, category_id, min_stock, supplier_id}
  Validation: sku unique, price > 0, name required
  Response: 201 {id, ...created product}
  Errors: 400 (validation), 401, 403, 409 (sku duplicate), 500
```

Return JSON with: base_path, endpoints list, openapi_yaml (abbreviated), \
pagination_strategy, filtering_strategy, error_format, rate_limiting."""


class APIContractSkill(BaseSkill[APIContractInput, APISpecification]):
    """Generates complete OpenAPI 3.1 API specifications."""

    name = "api_contract"
    description = "Generate complete REST API specification with auth, pagination, errors, and rate limiting"
    input_model = APIContractInput
    output_model = APISpecification

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: APIContractInput) -> APISpecification:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(APISpecification.model_json_schema(), indent=2)
        system = f"{_SYSTEM_PROMPT}\n\nOutput schema:\n```json\n{schema_json}\n```"

        user_content = (
            f"## Entities\n{json.dumps(input_data.entities[:20], indent=2, default=str)}"
            f"\n\n## User Workflows\n{json.dumps(input_data.user_workflows[:10], indent=2, default=str)}"
            f"\n\n## Business Rules\n{json.dumps(input_data.business_rules[:20], indent=2, default=str)}"
            f"\n\n## Auth Requirements\n" + "\n".join(f"- {r}" for r in input_data.auth_requirements)
        )

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return APISpecification.model_validate(parsed)
