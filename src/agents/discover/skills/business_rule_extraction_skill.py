"""BusinessRuleExtractionSkill: extracts detailed business rules from text.

Produces deep, specific rules with trigger conditions, actions, exceptions,
and validation logic — not shallow one-liners.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class BusinessRule(BaseModel):
    rule_id: str = ""
    rule_name: str = ""
    description: str = ""
    trigger_condition: str = ""
    action: str = ""
    exceptions: list[str] = Field(default_factory=list)
    source_reference: str = ""
    confidence: str = "medium"  # high, medium, low
    related_entities: list[str] = Field(default_factory=list)
    validation_logic: str = ""


class BusinessRuleExtractionInput(BaseModel):
    context_text: str
    source_type: str = "document"  # document, code, schema, meeting_notes


class BusinessRuleExtractionOutput(BaseModel):
    rules: list[BusinessRule] = Field(default_factory=list)


_SYSTEM_PROMPT = """\
You are a senior business analyst extracting DETAILED business rules from text.

For each rule you identify, provide:
- rule_id: a generated ID like "BR-001"
- rule_name: a short descriptive name
- description: full description of the rule
- trigger_condition: what causes this rule to fire
- action: what happens when the rule fires
- exceptions: edge cases or exceptions to the rule
- source_reference: which part of the input this comes from
- confidence: "high" if explicitly stated, "medium" if clearly implied, "low" if inferred
- related_entities: domain entities involved (e.g., User, Order, Payment)
- validation_logic: how to verify this rule is implemented correctly

## IMPORTANT: Deep extraction, not shallow

BAD (shallow): "Users can login"
GOOD (deep): "When a user fails 3 consecutive login attempts within 15 minutes, \
the account is locked for 30 minutes and an email notification is sent to the \
account owner and the security team. The lockout counter resets after a successful login."

BAD (shallow): "Orders have a total"
GOOD (deep): "Order total is calculated as: sum of (item_price * quantity) for all \
line items, minus any applicable discount codes (max 1 per order), plus sales tax \
calculated based on the shipping address state. Free shipping applies for orders \
over $50 before tax. If a discount code reduces the total below $0, the total is \
set to $0.00."

BAD (shallow): "Users must be authenticated"
GOOD (deep): "All API endpoints except /auth/login, /auth/register, and /health \
require a valid JWT token in the Authorization header (Bearer scheme). Tokens expire \
after 24 hours. Refresh tokens are valid for 30 days and can be used once — after \
use, a new refresh token is issued. Revoked tokens are checked against a Redis \
blacklist with TTL matching the token's remaining lifetime."

Return a JSON object with a "rules" array."""


class BusinessRuleExtractionSkill(
    BaseSkill[BusinessRuleExtractionInput, BusinessRuleExtractionOutput]
):
    """Extracts detailed business rules from text using LLM analysis."""

    name = "business_rule_extraction"
    description = "Extract detailed business rules with triggers, actions, and exceptions"
    input_model = BusinessRuleExtractionInput
    output_model = BusinessRuleExtractionOutput

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(
        self, input_data: BusinessRuleExtractionInput
    ) -> BusinessRuleExtractionOutput:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(BusinessRuleExtractionOutput.model_json_schema(), indent=2)
        system = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Output schema:\n```json\n{schema_json}\n```"
        )

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(
                content=(
                    f"Source type: {input_data.source_type}\n\n"
                    f"Extract all business rules from:\n\n{input_data.context_text}"
                )
            ),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return BusinessRuleExtractionOutput.model_validate(parsed)
