"""ConflictDetectionSkill: compares findings across sources to find inconsistencies."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class Conflict(BaseModel):
    conflict_type: str = ""  # contradiction, gap, ambiguity, redundancy
    source_a: str = ""
    source_b: str = ""
    description: str = ""
    suggested_resolution: str = ""
    severity: str = "warning"  # blocking, warning, info


class ConflictDetectionInput(BaseModel):
    findings: list[dict[str, Any]] = Field(default_factory=list)


class ConflictReport(BaseModel):
    contradictions: list[Conflict] = Field(default_factory=list)
    gaps: list[Conflict] = Field(default_factory=list)
    ambiguities: list[Conflict] = Field(default_factory=list)
    redundancies: list[Conflict] = Field(default_factory=list)
    total_conflicts: int = 0


_SYSTEM_PROMPT = """\
You are a senior analyst comparing findings extracted from multiple sources \
about a software system. Your job is to find inconsistencies.

Compare all findings and identify:

1. **Contradictions**: Source A says X, source B says Y (conflicting facts)
2. **Gaps**: Something mentioned in one source but missing from another \
(e.g., a business rule in the BRD with no corresponding code implementation)
3. **Ambiguities**: Vague or unclear requirements that could be interpreted \
multiple ways and need clarification
4. **Redundancies**: The same rule or requirement stated differently in \
multiple sources (note which version is more detailed/authoritative)

For each conflict, provide:
- conflict_type: "contradiction", "gap", "ambiguity", or "redundancy"
- source_a: which finding/source the first item comes from
- source_b: which finding/source the second item comes from (or "" for gaps/ambiguities)
- description: clear explanation of the conflict
- suggested_resolution: how to resolve it
- severity: "blocking" (must resolve before proceeding), "warning" (should resolve), \
"info" (nice to address)

Also set total_conflicts to the total number of all conflicts found.

Return a JSON object with arrays: contradictions, gaps, ambiguities, redundancies, \
and an integer total_conflicts."""


class ConflictDetectionSkill(
    BaseSkill[ConflictDetectionInput, ConflictReport]
):
    """Compares findings across sources to identify conflicts and gaps."""

    name = "conflict_detection"
    description = "Detect contradictions, gaps, ambiguities, and redundancies across findings"
    input_model = ConflictDetectionInput
    output_model = ConflictReport

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: ConflictDetectionInput) -> ConflictReport:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(ConflictReport.model_json_schema(), indent=2)
        system = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Output schema:\n```json\n{schema_json}\n```"
        )

        findings_json = json.dumps(input_data.findings, indent=2, default=str)

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(
                content=f"Compare these findings for conflicts:\n\n{findings_json}"
            ),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        report = ConflictReport.model_validate(parsed)

        # Ensure total_conflicts is accurate
        report.total_conflicts = (
            len(report.contradictions)
            + len(report.gaps)
            + len(report.ambiguities)
            + len(report.redundancies)
        )
        return report
