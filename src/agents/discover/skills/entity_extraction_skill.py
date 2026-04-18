"""EntityExtractionSkill: extracts domain entities and relationships from text."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class EntityAttribute(BaseModel):
    name: str = ""
    type: str = ""
    constraints: str = ""


class EntityRelationship(BaseModel):
    related_entity: str = ""
    relationship_type: str = ""  # has_many, belongs_to, has_one, many_to_many
    cardinality: str = ""  # 1:1, 1:N, N:M


class DomainEntity(BaseModel):
    entity_name: str = ""
    entity_type: str = ""  # user_role, data_object, process, system, location
    description: str = ""
    attributes: list[EntityAttribute] = Field(default_factory=list)
    relationships: list[EntityRelationship] = Field(default_factory=list)
    business_rules_involved: list[str] = Field(default_factory=list)


class EntityExtractionInput(BaseModel):
    text: str


class EntityExtractionOutput(BaseModel):
    entities: list[DomainEntity] = Field(default_factory=list)


_SYSTEM_PROMPT = """\
You are a domain modeling expert extracting entities from text about a software system.

For each entity, provide:
- entity_name: the name of the entity (e.g., "User", "Order", "Payment")
- entity_type: one of "user_role", "data_object", "process", "system", "location"
- description: what this entity represents in the domain
- attributes: list of {name, type, constraints} for each known attribute
- relationships: list of {related_entity, relationship_type, cardinality}
  where relationship_type is one of: has_many, belongs_to, has_one, many_to_many
  and cardinality is one of: 1:1, 1:N, N:M
- business_rules_involved: list of rule names/IDs that reference this entity

Be thorough. Extract entities from explicit mentions AND implied references.
Include both data entities (User, Order) and process entities (Checkout, Authentication).
Include system entities (Payment Gateway, Email Service) when external systems are mentioned.

Return a JSON object with an "entities" array."""


class EntityExtractionSkill(
    BaseSkill[EntityExtractionInput, EntityExtractionOutput]
):
    """Extracts domain entities with attributes and relationships from text."""

    name = "entity_extraction"
    description = "Extract domain entities, attributes, relationships, and linked business rules"
    input_model = EntityExtractionInput
    output_model = EntityExtractionOutput

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(
        self, input_data: EntityExtractionInput
    ) -> EntityExtractionOutput:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(EntityExtractionOutput.model_json_schema(), indent=2)
        system = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Output schema:\n```json\n{schema_json}\n```"
        )

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=f"Extract domain entities from:\n\n{input_data.text}"),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return EntityExtractionOutput.model_validate(parsed)
