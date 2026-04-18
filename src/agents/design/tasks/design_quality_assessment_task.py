"""DesignQualityAssessmentTask: validates completeness and consistency of design."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class DesignQualityScores(BaseModel):
    completeness: float = 0.0  # every entity has CRUD, every rule has enforcement
    consistency: float = 0.0  # schema matches API matches components
    feasibility: float = 0.0  # proposed stack can handle requirements
    traceability: float = 0.0  # every design decision traces to a requirement
    security: float = 0.0  # auth covers all protected resources


class DesignQualityAssessment(BaseModel):
    scores: DesignQualityScores = Field(default_factory=DesignQualityScores)
    overall_score: float = 0.0
    passing: bool = False
    gaps: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class DesignQualityInput(BaseModel):
    architecture: dict[str, Any] = Field(default_factory=dict)
    database_schema: dict[str, Any] = Field(default_factory=dict)
    api_specification: dict[str, Any] = Field(default_factory=dict)
    auth_design: dict[str, Any] = Field(default_factory=dict)
    frontend_components: dict[str, Any] = Field(default_factory=dict)
    structured_requirements: dict[str, Any] = Field(default_factory=dict)


class DesignQualityAssessmentTask(
    BaseTask[DesignQualityInput, DesignQualityAssessment]
):
    """Validates completeness, consistency, and feasibility of the full design."""

    name = "design_quality_assessment"
    description = (
        "Assess design quality: completeness (entity CRUD coverage, rule enforcement), "
        "consistency (schema↔API↔components alignment), feasibility, security"
    )
    input_schema = DesignQualityInput
    output_schema = DesignQualityAssessment

    prompt_template = """\
Evaluate the quality of this system design. Score each dimension 0-100:

**completeness** (0-100): Does every domain entity have CRUD endpoints? Does every \
business rule have an enforcement point (in API validation, DB constraint, or middleware)? \
Are all user workflows supported by the component architecture?

**consistency** (0-100): Does the database schema match the API request/response schemas? \
Do the frontend components consume the correct API endpoints? Are auth roles consistent \
across auth_design, API authorization, and frontend route guards?

**feasibility** (0-100): Can the proposed technology stack handle the non-functional \
requirements (performance, scalability, compliance)? Are there any technology mismatches?

**traceability** (0-100): Can every design decision be traced to a business requirement? \
Are there design elements with no requirement justification?

**security** (0-100): Does the auth design cover all protected resources? Are there \
unprotected endpoints? Password policy? Rate limiting? CSRF/CORS?

Set overall_score = (completeness * 0.3 + consistency * 0.25 + feasibility * 0.2 + \
traceability * 0.1 + security * 0.15)
Set passing = true if overall_score >= 70.
List specific gaps and improvement suggestions.

Architecture: {architecture}
Database Schema: {database_schema}
API Specification: {api_specification}
Auth Design: {auth_design}
Frontend Components: {frontend_components}
Requirements: {structured_requirements}"""

    few_shot_examples = [
        {
            "input": {
                "architecture": {"pattern": "modular_monolith"},
                "database_schema": {"tables": [{"name": "users"}, {"name": "orders"}]},
                "api_specification": {"endpoints": [{"path": "/users", "method": "GET"}]},
                "auth_design": {"roles": [{"name": "admin"}]},
                "frontend_components": {"pages": [{"name": "Dashboard"}]},
                "structured_requirements": {"entities": [{"entity_name": "User"}, {"entity_name": "Order"}]},
            },
            "output": {
                "scores": {"completeness": 40, "consistency": 60, "feasibility": 80, "traceability": 50, "security": 55},
                "overall_score": 54.5,
                "passing": False,
                "gaps": [
                    "Order entity has no CRUD endpoints",
                    "No POST/PUT/DELETE endpoints for users",
                    "Only admin role defined, no viewer or manager roles",
                    "No frontend pages for order management",
                ],
                "suggestions": [
                    "Add full CRUD for orders: GET /orders, POST /orders, PUT /orders/{id}, DELETE /orders/{id}",
                    "Add user management endpoints: POST /users, PUT /users/{id}",
                    "Define complete role hierarchy matching business requirements",
                ],
            },
        },
    ]

    def get_required_skills(self) -> list[str]:
        return []

    def validate(self, output: DesignQualityAssessment) -> bool:
        for field in ("completeness", "consistency", "feasibility", "traceability", "security"):
            val = getattr(output.scores, field)
            if val < 0 or val > 100:
                return False
        if output.overall_score < 0 or output.overall_score > 100:
            return False
        return True
