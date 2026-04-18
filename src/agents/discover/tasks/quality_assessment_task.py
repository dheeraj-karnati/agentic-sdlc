"""QualityAssessmentTask: scores discovery output for completeness and depth."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class QualityScores(BaseModel):
    completeness: float = 0.0  # 0-100
    depth: float = 0.0  # 0-100
    consistency: float = 0.0  # 0-100
    traceability: float = 0.0  # 0-100
    actionability: float = 0.0  # 0-100


class QualityAssessment(BaseModel):
    scores: QualityScores = Field(default_factory=QualityScores)
    overall_score: float = 0.0
    suggestions: list[str] = Field(default_factory=list)
    passing: bool = False


class QualityAssessmentInput(BaseModel):
    deep_analysis: dict[str, Any]
    system_understanding: dict[str, Any]
    clarification_questions: dict[str, Any]


class QualityAssessmentTask(
    BaseTask[QualityAssessmentInput, QualityAssessment]
):
    """Scores the overall discovery output on completeness, depth, and quality."""

    name = "quality_assessment"
    description = (
        "Score the discovery output on completeness, depth, consistency, "
        "traceability, and actionability. Determine if it meets the quality "
        "threshold for the Design Agent."
    )
    input_schema = QualityAssessmentInput
    output_schema = QualityAssessment

    prompt_template = """\
Evaluate the quality of this discovery analysis output. Score each dimension 0-100:

**completeness** (0-100): Are all major areas covered? Business rules, entities, \
technology stack, user workflows, integration points? Deduct points for missing areas.

**depth** (0-100): Are business rules detailed (triggers, actions, exceptions) or \
surface-level? Are entities fully described with attributes and relationships? \
Score 30 for shallow, 60 for moderate, 90+ for deep extraction.

**consistency** (0-100): Do findings across sources agree? Are there unresolved \
contradictions? Deduct 10 points per unresolved contradiction.

**traceability** (0-100): Can every finding be traced to a source? Are source \
references provided? Deduct points for unsourced claims.

**actionability** (0-100): Is the output sufficient for the Design Agent to \
produce a system design? Would a designer have enough detail to make architecture \
decisions?

Set overall_score = (completeness * 0.25 + depth * 0.3 + consistency * 0.2 + \
traceability * 0.1 + actionability * 0.15)

Set passing = true if overall_score >= 70.

If not passing, provide specific improvement suggestions.

Deep analysis results: {deep_analysis}
System understanding: {system_understanding}
Clarification questions: {clarification_questions}"""

    few_shot_examples = [
        {
            "input": {
                "deep_analysis": {"business_rules": [{"rule_name": "login"}], "entities": []},
                "system_understanding": {"system_purpose": "A short description."},
                "clarification_questions": {"questions": []},
            },
            "output": {
                "scores": {
                    "completeness": 30,
                    "depth": 20,
                    "consistency": 80,
                    "traceability": 40,
                    "actionability": 25,
                },
                "overall_score": 36.0,
                "suggestions": [
                    "Business rules need trigger conditions, actions, and exceptions — currently only names",
                    "No domain entities were extracted — entity extraction must be re-run",
                    "System purpose is one sentence — needs 2-3 paragraphs with business context",
                    "No user workflows identified — critical for Design Agent",
                ],
                "passing": False,
            },
        },
        {
            "input": {
                "deep_analysis": {
                    "business_rules": [
                        {"rule_name": "order_approval", "trigger_condition": "order > $10k"},
                        {"rule_name": "credit_check", "trigger_condition": "new customer"},
                    ],
                    "entities": [
                        {"entity_name": "Order", "attributes": ["id", "total", "status"]},
                        {"entity_name": "Customer", "attributes": ["id", "name", "credit_limit"]},
                    ],
                },
                "system_understanding": {
                    "system_purpose": "The Acme Order Management System is a B2B platform...(detailed)",
                    "user_workflows": [{"journey_name": "Place Order", "steps": ["1...", "2...", "3..."]}],
                },
                "clarification_questions": {"questions": [{"question": "Max login attempts?"}]},
            },
            "output": {
                "scores": {
                    "completeness": 85,
                    "depth": 75,
                    "consistency": 90,
                    "traceability": 70,
                    "actionability": 80,
                },
                "overall_score": 80.0,
                "suggestions": [],
                "passing": True,
            },
        },
    ]

    def get_required_skills(self) -> list[str]:
        return []  # Pure LLM assessment task

    def validate(self, output: QualityAssessment) -> bool:
        """Ensure scores are in valid range and overall_score is reasonable."""
        scores = output.scores
        for field in ("completeness", "depth", "consistency", "traceability", "actionability"):
            val = getattr(scores, field)
            if val < 0 or val > 100:
                return False
        if output.overall_score < 0 or output.overall_score > 100:
            return False
        return True
