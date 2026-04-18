"""PrototypeQualityAssessmentTask: evaluates prototype against Design spec."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class PrototypeQualityScores(BaseModel):
    page_coverage: float = 0.0  # all designed pages present?
    component_coverage: float = 0.0  # all specified components rendered?
    mock_data_quality: float = 0.0  # realistic domain data vs placeholder?
    navigation_completeness: float = 0.0  # all routes accessible?
    responsive_quality: float = 0.0  # no layout breaks on mobile?
    role_differentiation: float = 0.0  # different views per role?


class PrototypeQualityAssessment(BaseModel):
    scores: PrototypeQualityScores = Field(default_factory=PrototypeQualityScores)
    overall_score: float = 0.0
    passing: bool = False
    gaps: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class PrototypeQualityInput(BaseModel):
    prototype_spec: dict[str, Any] = Field(default_factory=dict)
    prototype_code: dict[str, Any] = Field(default_factory=dict)
    validation_result: dict[str, Any] = Field(default_factory=dict)


class PrototypeQualityAssessmentTask(
    BaseTask[PrototypeQualityInput, PrototypeQualityAssessment]
):
    """Evaluates prototype quality against the Design spec."""

    name = "prototype_quality_assessment"
    description = (
        "Score prototype on page coverage, component coverage, mock data quality, "
        "navigation, responsiveness, and role differentiation"
    )
    input_schema = PrototypeQualityInput
    output_schema = PrototypeQualityAssessment

    prompt_template = """\
Evaluate this prototype against its design specification. Score 0-100:

**page_coverage**: Are all designed pages present in the file tree?
**component_coverage**: Are all specified components implemented?
**mock_data_quality**: Is mock data realistic and domain-specific, or just placeholders?
**navigation_completeness**: Do all nav items link to existing routes?
**responsive_quality**: Is there evidence of responsive design (media queries, grid)?
**role_differentiation**: Are there different views for different user roles?

overall_score = average of all scores
passing = true if overall_score >= 70

Prototype spec: {prototype_spec}
Generated code files: {prototype_code}
Validation result: {validation_result}"""

    few_shot_examples = [
        {
            "input": {
                "prototype_spec": {"pages": [{"route": "/dashboard"}, {"route": "/products"}]},
                "prototype_code": {"file_tree": {"src/app/page.tsx": "..."}, "total_files": 1},
                "validation_result": {"passed": True, "route_count": 1},
            },
            "output": {
                "scores": {"page_coverage": 50, "component_coverage": 40, "mock_data_quality": 30,
                           "navigation_completeness": 50, "responsive_quality": 60, "role_differentiation": 0},
                "overall_score": 38.3,
                "passing": False,
                "gaps": ["Missing /products page", "No role-based views"],
                "suggestions": ["Add products page", "Add admin vs viewer differences"],
            },
        },
    ]

    def get_required_skills(self) -> list[str]:
        return []

    def validate(self, output: PrototypeQualityAssessment) -> bool:
        for field in ("page_coverage", "component_coverage", "mock_data_quality",
                      "navigation_completeness", "responsive_quality", "role_differentiation"):
            val = getattr(output.scores, field)
            if val < 0 or val > 100:
                return False
        return 0 <= output.overall_score <= 100
