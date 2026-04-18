"""DeepAnalysisTask: runs extraction skills across all classified inputs.

Takes ClassifiedInputs from ParseAndClassifyTask, dispatches to the
appropriate skills, cross-references entities, and runs conflict detection.
This is NOT an LLM task — it orchestrates skills directly.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.discover.skills.business_rule_extraction_skill import (
    BusinessRuleExtractionInput,
    BusinessRuleExtractionOutput,
    BusinessRuleExtractionSkill,
)
from src.agents.discover.skills.code_analysis_skill import (
    CodeAnalysisInput,
    CodeAnalysisResult,
    CodeAnalysisSkill,
)
from src.agents.discover.skills.conflict_detection_skill import (
    ConflictDetectionInput,
    ConflictDetectionSkill,
    ConflictReport,
)
from src.agents.discover.skills.document_extraction_skill import (
    DocumentExtractionInput,
    DocumentExtractionResult,
    DocumentExtractionSkill,
)
from src.agents.discover.skills.entity_extraction_skill import (
    EntityExtractionInput,
    EntityExtractionOutput,
    EntityExtractionSkill,
)
from src.agents.discover.skills.schema_analysis_skill import (
    SchemaAnalysisInput,
    SchemaAnalysisResult,
    SchemaAnalysisSkill,
)
from src.agents.discover.tasks.parse_and_classify_task import ClassifiedInputs

logger = logging.getLogger(__name__)


class DeepAnalysisInput(BaseModel):
    classified_inputs: ClassifiedInputs
    improvement_context: str = ""  # feedback from quality gate retry


class DeepAnalysisResult(BaseModel):
    code_analyses: list[dict[str, Any]] = Field(default_factory=list)
    document_extractions: list[dict[str, Any]] = Field(default_factory=list)
    schema_analyses: list[dict[str, Any]] = Field(default_factory=list)
    business_rules: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    conflict_report: dict[str, Any] = Field(default_factory=dict)
    all_extracted_text: str = ""


class DeepAnalysisTask(BaseTask[DeepAnalysisInput, DeepAnalysisResult]):
    """Orchestrates extraction skills across all classified inputs."""

    name = "deep_analysis"
    description = (
        "Run business rule extraction, entity extraction, and conflict "
        "detection across all classified inputs from the parse step"
    )
    input_schema = DeepAnalysisInput
    output_schema = DeepAnalysisResult
    prompt_template = ""  # Not used — this task calls skills directly
    few_shot_examples = []  # Not an LLM task

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm
        self._code_skill = CodeAnalysisSkill()
        self._doc_skill = DocumentExtractionSkill(llm=llm)
        self._schema_skill = SchemaAnalysisSkill()
        self._rule_skill = BusinessRuleExtractionSkill(llm=llm)
        self._entity_skill = EntityExtractionSkill(llm=llm)
        self._conflict_skill = ConflictDetectionSkill(llm=llm)

    def get_required_skills(self) -> list[str]:
        return [
            "code_analysis",
            "document_extraction",
            "schema_analysis",
            "business_rule_extraction",
            "entity_extraction",
            "conflict_detection",
        ]

    async def execute(
        self,
        input_data: DeepAnalysisInput,
        *,
        llm: Any | None = None,
    ) -> DeepAnalysisResult:
        """Run all extraction skills and cross-reference results.

        Overrides BaseTask.execute() because this task orchestrates skills
        rather than calling an LLM with a prompt template.
        """
        classified = input_data.classified_inputs
        code_results: list[dict[str, Any]] = []
        doc_results: list[dict[str, Any]] = []
        schema_results: list[dict[str, Any]] = []
        all_text_parts: list[str] = []

        # Phase 1: Dispatch to type-specific extraction skills
        for item in classified.items:
            all_text_parts.append(item.content)
            ct = item.content_type

            if ct == "source_code":
                result = await self._code_skill.run(
                    CodeAnalysisInput(source_code=item.content, language=item.language)
                )
                code_results.append(result.model_dump(mode="json"))

            elif ct in ("brd", "srs", "meeting_notes", "manual"):
                result = await self._doc_skill.run(
                    DocumentExtractionInput(
                        document_text=item.content, document_type=ct
                    )
                )
                doc_results.append(result.model_dump(mode="json"))

            elif ct == "schema":
                result = await self._schema_skill.run(
                    SchemaAnalysisInput(sql_or_schema=item.content)
                )
                schema_results.append(result.model_dump(mode="json"))

            elif ct == "api_doc":
                # Treat API docs like BRDs for extraction
                result = await self._doc_skill.run(
                    DocumentExtractionInput(
                        document_text=item.content, document_type="brd"
                    )
                )
                doc_results.append(result.model_dump(mode="json"))

        all_text = "\n\n---\n\n".join(all_text_parts)

        # Phase 2: Run cross-cutting skills on ALL text
        rules_result = await self._rule_skill.run(
            BusinessRuleExtractionInput(
                context_text=all_text[:15000],  # Limit for LLM context
                source_type="mixed",
            )
        )

        entities_result = await self._entity_skill.run(
            EntityExtractionInput(text=all_text[:15000])
        )

        # Phase 3: Conflict detection across all findings
        all_findings: list[dict[str, Any]] = []
        for cr in code_results:
            all_findings.append({"source": "code_analysis", "data": cr})
        for dr in doc_results:
            all_findings.append({"source": "document_extraction", "data": dr})
        for sr in schema_results:
            all_findings.append({"source": "schema_analysis", "data": sr})
        all_findings.append({
            "source": "business_rules",
            "data": rules_result.model_dump(mode="json"),
        })
        all_findings.append({
            "source": "entities",
            "data": entities_result.model_dump(mode="json"),
        })

        conflict_result = await self._conflict_skill.run(
            ConflictDetectionInput(findings=all_findings)
        )

        return DeepAnalysisResult(
            code_analyses=code_results,
            document_extractions=doc_results,
            schema_analyses=schema_results,
            business_rules=rules_result.model_dump(mode="json").get("rules", []),
            entities=entities_result.model_dump(mode="json").get("entities", []),
            conflict_report=conflict_result.model_dump(mode="json"),
            all_extracted_text=all_text[:20000],
        )
