"""Validate API Contracts Task — validates implementation against OpenAPI specification."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class ValidateAPIContractsInput(BaseModel):
    """Input for API contract validation task."""

    openapi_spec: dict = Field(description="OpenAPI specification to validate against")
    implemented_endpoints: list[dict] = Field(description="Implemented API endpoints")


class APIValidationOutput(BaseModel):
    """Output of API contract validation task."""

    validation_result: dict = Field(default_factory=dict, description="Detailed validation results")
    compliant: bool = Field(default=False, description="Whether the implementation is spec-compliant")


class ValidateAPIContractsTask(BaseTask[ValidateAPIContractsInput, APIValidationOutput]):
    """Validates that API implementation matches the OpenAPI specification."""

    name: str = "validate_api_contracts"
    description: str = "Validate API implementation against the OpenAPI specification"
    input_schema = ValidateAPIContractsInput
    output_schema = APIValidationOutput
    prompt_template: str = ""
    few_shot_examples: list[dict[str, Any]] = []

    def get_required_skills(self) -> list[str]:
        """Return skills this task depends on."""
        return ["api_contract_validation"]
