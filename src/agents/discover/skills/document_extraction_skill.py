"""DocumentExtractionSkill: extracts structured data from documents using LLM.

Handles BRDs, SRS docs, meeting notes, and manuals — each with a
document-type-specific extraction prompt and output schema.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


# ─── Output Sub-Models ───


class Requirement(BaseModel):
    id: str = ""
    description: str = ""
    priority: str = "medium"  # high, medium, low
    source_section: str = ""
    type: str = "functional"  # functional, non_functional


class NonFunctionalRequirement(BaseModel):
    category: str = ""  # performance, security, scalability, etc.
    description: str = ""
    metric: str = ""
    target_value: str = ""


class ActionItem(BaseModel):
    assignee: str = ""
    action: str = ""
    due_date: str = ""
    status: str = "open"


class UserWorkflow(BaseModel):
    workflow_name: str = ""
    steps: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)


class DocumentExtractionInput(BaseModel):
    document_text: str
    document_type: str = "brd"  # brd, srs, meeting_notes, manual


class DocumentExtractionResult(BaseModel):
    document_type: str = ""
    # BRD / SRS fields
    stakeholders: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    scope: str = ""
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    functional_requirements: list[Requirement] = Field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirement] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    # Meeting notes fields
    decisions_made: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    attendees: list[str] = Field(default_factory=list)
    # Manual fields
    features_described: list[str] = Field(default_factory=list)
    user_workflows: list[UserWorkflow] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    # Raw extracted text for downstream use
    raw_extracted_text: str = ""


# ─── Prompts by document type ───

_BRD_PROMPT = """\
You are a senior business analyst extracting structured data from a \
Business Requirements Document (BRD) or Software Requirements Specification (SRS).

Extract ALL of the following into JSON:
- stakeholders: list of people/roles mentioned
- objectives: list of business objectives
- scope: description of what's in scope
- constraints: list of constraints (budget, timeline, technology, regulatory)
- assumptions: list of assumptions made
- functional_requirements: list of requirements, each with id, description, \
priority (high/medium/low), source_section, type ("functional")
- non_functional_requirements: list with category (performance/security/scalability/\
reliability/usability), description, metric, target_value
- acceptance_criteria: list of acceptance criteria
- out_of_scope: list of items explicitly out of scope

Be thorough. Extract every requirement even if it is implied. \
For each requirement, assign a priority based on the language used \
(e.g., "must" = high, "should" = medium, "could" = low)."""

_MEETING_PROMPT = """\
You are a senior business analyst extracting structured data from meeting notes.

Extract ALL of the following into JSON:
- attendees: list of names/roles present
- decisions_made: list of decisions reached in the meeting
- action_items: list with assignee, action, due_date, status
- open_questions: list of unresolved questions or topics requiring follow-up

Be thorough. Capture every decision and action item, even if informal."""

_MANUAL_PROMPT = """\
You are a senior business analyst extracting structured data from a user manual \
or product documentation.

Extract ALL of the following into JSON:
- features_described: list of features/capabilities described
- user_workflows: list with workflow_name, steps (ordered list), actors (roles involved)
- business_rules: list of business rules embedded in the documentation

Be thorough. Every workflow step should be captured in order."""

_PROMPTS: dict[str, str] = {
    "brd": _BRD_PROMPT,
    "srs": _BRD_PROMPT,
    "meeting_notes": _MEETING_PROMPT,
    "manual": _MANUAL_PROMPT,
}


class DocumentExtractionSkill(BaseSkill[DocumentExtractionInput, DocumentExtractionResult]):
    """Extracts structured data from documents using LLM-based analysis."""

    name = "document_extraction"
    description = "Extract structured requirements, rules, and workflows from documents"
    input_model = DocumentExtractionInput
    output_model = DocumentExtractionResult

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(
        self, input_data: DocumentExtractionInput
    ) -> DocumentExtractionResult:
        llm = self._llm or get_llm(max_tokens=8192)
        doc_type = input_data.document_type.lower()
        system_prompt = _PROMPTS.get(doc_type, _BRD_PROMPT)

        schema_json = json.dumps(DocumentExtractionResult.model_json_schema(), indent=2)
        full_system = (
            f"{system_prompt}\n\n"
            f"Return your response as JSON matching this schema:\n```json\n{schema_json}\n```"
        )

        response = await llm.ainvoke([
            SystemMessage(content=full_system),
            HumanMessage(content=f"Extract from this {doc_type} document:\n\n{input_data.document_text}"),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        result = DocumentExtractionResult.model_validate(parsed)
        result.document_type = doc_type
        result.raw_extracted_text = input_data.document_text[:5000]
        return result
