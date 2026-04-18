"""E2E Test Generation Skill — generates end-to-end test suites from user stories and API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill


class E2ETestInput(BaseModel):
    """Input for E2E test generation."""

    user_stories: list[dict] = Field(description="User stories to generate tests for")
    api_endpoints: list[dict] = Field(description="API endpoints to test against")


class TestCase(BaseModel):
    """A single E2E test case."""

    name: str = Field(description="Test case name")
    description: str = Field(description="What the test verifies")
    steps: list[str] = Field(default_factory=list, description="Ordered test steps")
    expected_result: str = Field(default="", description="Expected outcome")
    priority: str = Field(default="medium", description="Test priority: high, medium, low")


class E2ETestSuite(BaseModel):
    """Output containing generated E2E test cases."""

    test_cases: list[TestCase] = Field(default_factory=list, description="Generated test cases")
    framework: str = Field(default="", description="Recommended test framework")
    setup_instructions: str = Field(default="", description="Setup instructions for the test suite")


class E2ETestGenerationSkill(BaseSkill[E2ETestInput, E2ETestSuite]):
    """Generates end-to-end test suites from user stories and API endpoint specifications."""

    name: str = "e2e_test_generation"
    description: str = "Generate E2E test suites from user stories and API endpoints"
    input_model = E2ETestInput
    output_model = E2ETestSuite

    async def execute(self, input_data: E2ETestInput) -> E2ETestSuite:
        """Generate E2E test suite. Not yet implemented."""
        raise NotImplementedError("Not yet implemented")
