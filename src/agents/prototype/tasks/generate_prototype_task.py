"""GeneratePrototypeTask: generates and validates a prototype application."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.prototype.skills.design_interpreter_skill import PrototypeSpec
from src.agents.prototype.skills.prototype_validator_skill import (
    PrototypeValidatorInput,
    PrototypeValidatorSkill,
)
from src.agents.prototype.skills.ui_generator_skill import (
    PrototypeCode,
    UIGeneratorInput,
    UIGeneratorSkill,
)

logger = logging.getLogger(__name__)


class GeneratePrototypeInput(BaseModel):
    prototype_spec: dict[str, Any]
    feedback_history: list[dict[str, Any]] = Field(default_factory=list)
    business_context_summary: str = ""


class GeneratePrototypeOutput(BaseModel):
    prototype_code: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)


class GeneratePrototypeTask(BaseTask[GeneratePrototypeInput, GeneratePrototypeOutput]):
    """Generates a prototype app and validates it, retrying on validation failure."""

    name = "generate_prototype"
    description = "Generate Next.js prototype code and validate structure, retrying on failure"
    input_schema = GeneratePrototypeInput
    output_schema = GeneratePrototypeOutput
    prompt_template = ""
    few_shot_examples = []
    max_validation_retries: int = 2

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm
        self._generator = UIGeneratorSkill(llm=llm)
        self._validator = PrototypeValidatorSkill()

    def get_required_skills(self) -> list[str]:
        return ["ui_generator", "prototype_validator"]

    async def execute(self, input_data: GeneratePrototypeInput, *, llm: Any | None = None) -> GeneratePrototypeOutput:
        spec = PrototypeSpec.model_validate(input_data.prototype_spec)
        expected_routes = [p.route for p in spec.pages]

        gen_input = UIGeneratorInput(
            prototype_spec=spec,
            feedback_history=input_data.feedback_history,
            business_context_summary=input_data.business_context_summary,
        )

        for attempt in range(1 + self.max_validation_retries):
            code = await self._generator.run(gen_input)

            validation = await self._validator.run(
                PrototypeValidatorInput(
                    prototype_code=code,
                    expected_routes=expected_routes,
                )
            )

            if validation.passed:
                return GeneratePrototypeOutput(
                    prototype_code=code.model_dump(mode="json"),
                    validation=validation.model_dump(mode="json"),
                )

            if attempt < self.max_validation_retries:
                logger.warning(
                    "Prototype validation failed (attempt %d/%d): %s",
                    attempt + 1, self.max_validation_retries + 1,
                    validation.errors,
                )
                # Add validation errors as feedback for retry
                gen_input.feedback_history = list(gen_input.feedback_history) + [
                    {"type": "validation_error", "errors": validation.errors,
                     "warnings": validation.warnings}
                ]

        # Return even if validation failed after retries
        return GeneratePrototypeOutput(
            prototype_code=code.model_dump(mode="json"),
            validation=validation.model_dump(mode="json"),
        )
