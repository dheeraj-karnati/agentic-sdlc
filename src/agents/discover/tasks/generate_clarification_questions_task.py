"""GenerateClarificationQuestionsTask: produces prioritized questions from conflicts/gaps."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class ClarificationQuestion(BaseModel):
    question: str = ""
    why_asking: str = ""
    impact_if_unanswered: str = ""
    suggested_options: list[str] = Field(default_factory=list)
    related_findings: list[str] = Field(default_factory=list)
    priority: str = "important"  # blocking, important, nice_to_have


class ClarificationQuestionsInput(BaseModel):
    conflict_report: dict[str, Any]
    entities: list[dict[str, Any]] = Field(default_factory=list)
    business_rules: list[dict[str, Any]] = Field(default_factory=list)


class ClarificationQuestionsOutput(BaseModel):
    questions: list[ClarificationQuestion] = Field(default_factory=list)


class GenerateClarificationQuestionsTask(
    BaseTask[ClarificationQuestionsInput, ClarificationQuestionsOutput]
):
    """Generates prioritized clarification questions from conflicts and gaps."""

    name = "generate_clarification_questions"
    description = (
        "Generate prioritized clarification questions based on conflicts, "
        "gaps, and ambiguities found during deep analysis"
    )
    input_schema = ClarificationQuestionsInput
    output_schema = ClarificationQuestionsOutput

    prompt_template = """\
Based on the conflicts, gaps, and ambiguities identified in the analysis, \
generate targeted clarification questions for the product owner.

Rules:
- Only ask about genuinely unclear items. Do not ask obvious questions.
- Each question must explain WHY you are asking (what decision it unblocks).
- Provide suggested answer options so the PO can quickly respond.
- Prioritize: "blocking" = must answer before design can proceed, \
"important" = should answer soon, "nice_to_have" = optional but helpful.

Conflict report: {conflict_report}
Entities found: {entities}
Business rules found: {business_rules}"""

    few_shot_examples = [
        {
            "input": {
                "conflict_report": {
                    "contradictions": [
                        {
                            "description": "BRD says max 5 login attempts, code allows 3",
                            "source_a": "BRD section 3.2",
                            "source_b": "auth_service.py line 45",
                        }
                    ],
                    "gaps": [
                        {
                            "description": "BRD mentions 'audit logging' but no code implements it",
                        }
                    ],
                },
                "entities": [],
                "business_rules": [],
            },
            "output": {
                "questions": [
                    {
                        "question": "What should the maximum number of failed login attempts be before account lockout?",
                        "why_asking": "The BRD specifies 5 attempts but the current code enforces 3 attempts. The modernized system needs one definitive number.",
                        "impact_if_unanswered": "The authentication module design cannot be finalized — this affects security posture and user experience.",
                        "suggested_options": [
                            "3 attempts (current code behavior)",
                            "5 attempts (BRD specification)",
                            "Configurable per-tenant",
                        ],
                        "related_findings": [
                            "BRD section 3.2: max login attempts",
                            "auth_service.py: MAX_ATTEMPTS = 3",
                        ],
                        "priority": "blocking",
                    },
                    {
                        "question": "What level of audit logging is required for the modernized system?",
                        "why_asking": "The BRD mentions audit logging as a requirement but the legacy system has no implementation. We need to know the scope to design the logging infrastructure.",
                        "impact_if_unanswered": "Cannot size the logging infrastructure or determine which events need to be captured. May need dedicated audit table or external service.",
                        "suggested_options": [
                            "Basic: login/logout and data modifications only",
                            "Standard: all user actions with timestamps",
                            "Comprehensive: all API calls, data access, and admin actions (compliance-grade)",
                        ],
                        "related_findings": [
                            "BRD section 5.1: 'System must provide comprehensive audit logging'",
                        ],
                        "priority": "important",
                    },
                ],
            },
        },
    ]

    def get_required_skills(self) -> list[str]:
        return []  # Pure LLM task

    def validate(self, output: ClarificationQuestionsOutput) -> bool:
        """Ensure questions are meaningful."""
        for q in output.questions:
            if not q.question or not q.why_asking:
                return False
        return True
