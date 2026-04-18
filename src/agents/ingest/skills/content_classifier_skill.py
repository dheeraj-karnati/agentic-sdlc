"""ContentClassifierSkill: classifies content type using LLM."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class ContentClassificationInput(BaseModel):
    raw_text: str
    source_filename: str = ""


class ContentClassification(BaseModel):
    content_type: str = "unknown"  # brd, srs, prd, meeting_notes, user_manual, api_documentation, technical_spec, architecture_doc, test_plan, change_request, email_thread, source_code, schema, unknown
    language: str = "en"
    domain: str = ""
    formality_level: str = "formal"  # formal, semi_formal, informal
    estimated_completeness: float = 0.0  # 0-1
    key_topics: list[str] = Field(default_factory=list)
    confidence: float = 0.0


_SYSTEM_PROMPT = """\
You are a document classification expert. Classify the given text by content type.

Content types:
- brd: Business Requirements Document
- srs: Software Requirements Specification
- prd: Product Requirements Document
- meeting_notes: Meeting minutes or discussion notes
- user_manual: User or operator manual/guide
- api_documentation: API reference or specification
- technical_spec: Technical specification or architecture document
- architecture_doc: System architecture description
- test_plan: Test plan or QA documentation
- change_request: Change request or feature request
- email_thread: Email conversation
- source_code: Programming source code
- schema: Database schema or data model definition
- unknown: Cannot determine

Return JSON with: content_type, language (ISO code), domain (business area), \
formality_level (formal/semi_formal/informal), estimated_completeness (0-1), \
key_topics (list of 3-5 topics), confidence (0-1)."""


class ContentClassifierSkill(BaseSkill[ContentClassificationInput, ContentClassification]):
    """Classifies text content type using LLM analysis."""

    name = "content_classifier"
    description = "Classify document content type, language, domain, and completeness"
    input_model = ContentClassificationInput
    output_model = ContentClassification

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: ContentClassificationInput) -> ContentClassification:
        llm = self._llm or get_llm(max_tokens=1024)
        preview = input_data.raw_text[:2000]

        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Filename: {input_data.source_filename}\n\nText preview:\n{preview}"),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return ContentClassification.model_validate(parsed)
