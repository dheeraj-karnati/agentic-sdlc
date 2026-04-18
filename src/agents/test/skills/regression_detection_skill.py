"""Regression Detection Skill — compares current vs previous test results for regressions."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill


class RegressionInput(BaseModel):
    """Input for regression detection."""

    previous_results: dict = Field(description="Previous test/scan results baseline")
    current_results: dict = Field(description="Current test/scan results to compare")


class RegressionReport(BaseModel):
    """Output of regression detection."""

    regressions: list[str] = Field(default_factory=list, description="Detected regressions")
    improvements: list[str] = Field(default_factory=list, description="Detected improvements")
    stable: list[str] = Field(default_factory=list, description="Areas with no change")


class RegressionDetectionSkill(BaseSkill[RegressionInput, RegressionReport]):
    """Compares current and previous results to detect regressions and improvements."""

    name: str = "regression_detection"
    description: str = "Detect regressions by comparing current vs previous results"
    input_model = RegressionInput
    output_model = RegressionReport

    async def execute(self, input_data: RegressionInput) -> RegressionReport:
        """Run regression detection. Not yet implemented."""
        raise NotImplementedError("Not yet implemented")
