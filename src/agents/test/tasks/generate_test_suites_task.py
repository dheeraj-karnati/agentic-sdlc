"""Generate Test Suites Task — orchestrates test generation from stories, API spec, and components."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class GenerateTestSuitesInput(BaseModel):
    """Input for test suite generation."""

    user_stories: list[dict] = Field(description="User stories to generate tests for")
    api_specification: dict = Field(default_factory=dict, description="API specification")
    component_specs: list[dict] = Field(default_factory=list, description="UI component specifications")


class TestSuitesOutput(BaseModel):
    """Output containing generated test suites."""

    e2e_tests: dict = Field(default_factory=dict, description="End-to-end test suite")
    integration_tests: dict = Field(default_factory=dict, description="Integration test suite")
    unit_test_guidelines: dict = Field(default_factory=dict, description="Unit test guidelines and patterns")


class GenerateTestSuitesTask(BaseTask[GenerateTestSuitesInput, TestSuitesOutput]):
    """Generates comprehensive test suites from user stories, API specs, and component specs."""

    name: str = "generate_test_suites"
    description: str = (
        "Generate E2E, integration, and unit test suites from user stories, "
        "API specifications, and component specs"
    )
    input_schema = GenerateTestSuitesInput
    output_schema = TestSuitesOutput
    prompt_template: str = ""
    few_shot_examples: list[dict[str, Any]] = []

    def get_required_skills(self) -> list[str]:
        """Return skills this task depends on."""
        return ["e2e_test_generation", "coverage_analysis"]
