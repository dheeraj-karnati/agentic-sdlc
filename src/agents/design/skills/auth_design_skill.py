"""AuthDesignSkill: generates complete authentication and authorization architecture."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class Permission(BaseModel):
    name: str = ""
    description: str = ""
    resource: str = ""
    actions: list[str] = Field(default_factory=list)  # create, read, update, delete, approve, etc.


class RoleDefinition(BaseModel):
    name: str = ""
    description: str = ""
    permissions: list[str] = Field(default_factory=list)
    inherits_from: str = ""  # role hierarchy


class TokenConfig(BaseModel):
    type: str = ""  # access, refresh
    expiry: str = ""  # e.g. "15m", "30d"
    rotation_policy: str = ""
    storage: str = ""  # httponly_cookie, local_storage, memory


class SecurityMeasure(BaseModel):
    measure: str = ""
    description: str = ""
    configuration: str = ""


class AuthDesignInput(BaseModel):
    user_roles: list[dict[str, Any]] = Field(default_factory=list)
    business_rules: list[dict[str, Any]] = Field(default_factory=list)
    security_requirements: list[str] = Field(default_factory=list)


class AuthDesign(BaseModel):
    auth_strategy: str = ""  # jwt, session, oauth2
    oauth2_flows: list[str] = Field(default_factory=list)
    token_management: list[TokenConfig] = Field(default_factory=list)
    roles: list[RoleDefinition] = Field(default_factory=list)
    permissions: list[Permission] = Field(default_factory=list)
    permission_matrix: dict[str, list[str]] = Field(default_factory=dict)  # role -> [permissions]
    middleware_design: str = ""
    security_measures: list[SecurityMeasure] = Field(default_factory=list)
    password_policy: str = ""
    session_management: str = ""


_SYSTEM_PROMPT = """\
You are a senior security architect designing an authentication and authorization system.

Design a complete auth architecture based on the provided user roles, business rules, \
and security requirements.

Include:
- Auth strategy: JWT with access+refresh tokens, or session-based, or OAuth2 flows
- Token management: expiry, rotation, revocation, storage
- RBAC model: roles, permissions, permission matrix, role hierarchy
- Middleware design: how auth guards/decorators work
- Security measures: password hashing (bcrypt, argon2), rate limiting on auth endpoints, \
account lockout rules, CSRF protection, CORS policy
- Password policy: complexity, rotation, history
- Session management: expiry, concurrent sessions, device tracking

Map EVERY role-related business rule to a specific permission and middleware enforcement point.

Return JSON matching the output schema."""


class AuthDesignSkill(BaseSkill[AuthDesignInput, AuthDesign]):
    """Generates complete authentication and authorization architecture."""

    name = "auth_design"
    description = "Design complete auth system with RBAC, token management, and security measures"
    input_model = AuthDesignInput
    output_model = AuthDesign

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: AuthDesignInput) -> AuthDesign:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(AuthDesign.model_json_schema(), indent=2)
        system = f"{_SYSTEM_PROMPT}\n\nOutput schema:\n```json\n{schema_json}\n```"

        user_content = (
            f"## User Roles\n{json.dumps(input_data.user_roles[:10], indent=2, default=str)}"
            f"\n\n## Business Rules (auth-related)\n{json.dumps(input_data.business_rules[:20], indent=2, default=str)}"
            f"\n\n## Security Requirements\n" + "\n".join(f"- {r}" for r in input_data.security_requirements)
        )

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return AuthDesign.model_validate(parsed)
