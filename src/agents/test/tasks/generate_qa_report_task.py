"""Generate QA Report Task — produces a final quality assurance report from all results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class GenerateQAReportInput(BaseModel):
    """Input for QA report generation."""

    all_results: dict = Field(description="Aggregated results from all QA tasks")


class QAReport(BaseModel):
    """Final QA report output."""

    summary: str = Field(default="", description="Executive summary of QA findings")
    overall_score: float = Field(default=0.0, description="Overall quality score 0-100")
    passing: bool = Field(default=False, description="Whether quality gates are met")
    blocking_issues: list[str] = Field(default_factory=list, description="Issues blocking release")
    recommendations: list[str] = Field(default_factory=list, description="Improvement recommendations")


class GenerateQAReportTask(BaseTask[GenerateQAReportInput, QAReport]):
    """Generates a comprehensive QA report summarizing all test and scan results."""

    name: str = "generate_qa_report"
    description: str = (
        "Generate a comprehensive QA report from all test, scan, "
        "and verification results"
    )
    input_schema = GenerateQAReportInput
    output_schema = QAReport
    prompt_template: str = ""
    few_shot_examples: list[dict[str, Any]] = []

    def get_required_skills(self) -> list[str]:
        """Return skills this task depends on."""
        return ["regression_detection", "coverage_analysis"]
