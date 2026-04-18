"""Verify Acceptance Criteria Task — verifies test results against user story ACs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class VerifyACInput(BaseModel):
    """Input for acceptance criteria verification task."""

    stories: list[dict] = Field(description="User stories with acceptance criteria")
    test_results: list[dict] = Field(description="Test results to verify")


class ACReportOutput(BaseModel):
    """Output of acceptance criteria verification task."""

    verification: dict = Field(default_factory=dict, description="Detailed verification results")
    overall_pass_rate: float = Field(default=0.0, description="Overall AC pass rate 0-100")
    release_ready: bool = Field(default=False, description="Whether the build is release-ready")


class VerifyAcceptanceCriteriaTask(BaseTask[VerifyACInput, ACReportOutput]):
    """Verifies test results against user story acceptance criteria for release readiness."""

    name: str = "verify_acceptance_criteria"
    description: str = "Verify test results against acceptance criteria and assess release readiness"
    input_schema = VerifyACInput
    output_schema = ACReportOutput
    prompt_template: str = ""
    few_shot_examples: list[dict[str, Any]] = []

    def get_required_skills(self) -> list[str]:
        """Return skills this task depends on."""
        return ["acceptance_criteria_verification"]
