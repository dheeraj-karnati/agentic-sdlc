"""API Contract Validation Skill — validates implementation against OpenAPI spec."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill


class ContractValidationInput(BaseModel):
    """Input for API contract validation."""

    openapi_spec: dict = Field(description="OpenAPI specification to validate against")
    implementation_endpoints: list[dict] = Field(description="Implemented API endpoints")


class ContractValidationResult(BaseModel):
    """Output of API contract validation."""

    mismatches: list[str] = Field(default_factory=list, description="Spec vs implementation mismatches")
    missing_endpoints: list[str] = Field(default_factory=list, description="Endpoints in spec but not implemented")
    extra_endpoints: list[str] = Field(default_factory=list, description="Endpoints implemented but not in spec")
    valid: bool = Field(default=False, description="Whether the implementation matches the spec")


class APIContractValidationSkill(BaseSkill[ContractValidationInput, ContractValidationResult]):
    """Validates API implementation against an OpenAPI specification."""

    name: str = "api_contract_validation"
    description: str = "Validate API implementation against OpenAPI spec"
    input_model = ContractValidationInput
    output_model = ContractValidationResult

    async def execute(self, input_data: ContractValidationInput) -> ContractValidationResult:
        """Run API contract validation. Not yet implemented."""
        raise NotImplementedError("Not yet implemented")
