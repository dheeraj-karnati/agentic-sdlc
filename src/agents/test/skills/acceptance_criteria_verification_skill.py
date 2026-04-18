"""Acceptance Criteria Verification Skill — verifies test results against user story ACs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill


class ACVerificationInput(BaseModel):
    """Input for acceptance criteria verification."""

    user_stories: list[dict] = Field(description="User stories with acceptance criteria")
    test_results: list[dict] = Field(description="Test results to verify against ACs")


class ACVerificationResult(BaseModel):
    """Output of acceptance criteria verification."""

    verified: list[str] = Field(default_factory=list, description="ACs that passed verification")
    failed: list[str] = Field(default_factory=list, description="ACs that failed verification")
    untested: list[str] = Field(default_factory=list, description="ACs with no matching tests")
    pass_rate: float = Field(default=0.0, description="Percentage of ACs passing 0-100")


class AcceptanceCriteriaVerificationSkill(BaseSkill[ACVerificationInput, ACVerificationResult]):
    """Verifies test results against user story acceptance criteria."""

    name: str = "acceptance_criteria_verification"
    description: str = "Verify test results against user story acceptance criteria"
    input_model = ACVerificationInput
    output_model = ACVerificationResult

    async def execute(self, input_data: ACVerificationInput) -> ACVerificationResult:
        """Run AC verification. Not yet implemented."""
        raise NotImplementedError("Not yet implemented")
