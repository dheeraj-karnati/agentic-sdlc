"""BaseTask: focused unit of work combining prompt + LLM call + output validation.

Tasks are the middle layer between Skills (stateless capabilities) and
Workflows (state machines). Each task has a prompt template, few-shot
examples, and typed input/output schemas. Tasks handle LLM output
parsing, validation, and retry with corrective feedback.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm

logger = logging.getLogger(__name__)

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseTask(ABC, Generic[InputT, OutputT]):
    """Abstract base for all tasks.

    Subclasses must define:
        name:              short identifier
        description:       what the task does
        input_schema:      Pydantic model class for input
        output_schema:     Pydantic model class for output
        prompt_template:   string with {placeholders} for input fields
        few_shot_examples: list of {"input": ..., "output": ...} dicts

    And optionally override:
        validate(output) -> bool   custom validation beyond schema
        get_system_prompt() -> str custom system context
    """

    name: str = ""
    description: str = ""
    input_schema: type[InputT]  # type: ignore[assignment]
    output_schema: type[OutputT]  # type: ignore[assignment]
    prompt_template: str = ""
    few_shot_examples: list[dict[str, Any]] = []
    max_retries: int = 2

    def validate(self, output: OutputT) -> bool:
        """Optional custom validation beyond Pydantic schema parsing.

        Return True if valid. Override to add domain-specific checks.
        """
        return True

    def get_system_prompt(self) -> str:
        """Return the system prompt with role context and output format instructions."""
        schema_json = json.dumps(
            self.output_schema.model_json_schema(), indent=2
        )
        return (
            f"You are an expert software analyst performing the task: {self.description}\n\n"
            f"You MUST return your response as a valid JSON object that conforms to this schema:\n"
            f"```json\n{schema_json}\n```\n\n"
            f"Return ONLY the JSON object, no additional text or explanation."
        )

    def _render_prompt(self, input_data: InputT) -> str:
        """Render the prompt template with input data and few-shot examples."""
        parts: list[str] = []

        # Few-shot examples
        if self.few_shot_examples:
            parts.append("## Examples of good output\n")
            for i, example in enumerate(self.few_shot_examples, 1):
                parts.append(f"### Example {i}")
                parts.append(f"**Input:** {json.dumps(example['input'], indent=2)}")
                parts.append(f"**Output:** {json.dumps(example['output'], indent=2)}")
                parts.append("")

        # Main instruction with input data
        parts.append("## Your task\n")
        input_dict = input_data.model_dump(mode="json")
        rendered = self.prompt_template.format(**input_dict)
        parts.append(rendered)

        # Append full input as structured data
        parts.append("\n## Input data\n")
        parts.append(f"```json\n{json.dumps(input_dict, indent=2)}\n```")

        return "\n".join(parts)

    def _render_retry_prompt(
        self, original_prompt: str, raw_output: str, errors: list[str]
    ) -> str:
        """Build a corrective feedback prompt for retry."""
        error_text = "\n".join(f"- {e}" for e in errors)
        return (
            f"{original_prompt}\n\n"
            f"---\n"
            f"Your previous output failed validation. Here was your output:\n"
            f"```json\n{raw_output}\n```\n\n"
            f"Please fix the following issues and try again:\n{error_text}\n\n"
            f"Return ONLY the corrected JSON object."
        )

    async def execute(
        self,
        input_data: InputT,
        *,
        llm: Any | None = None,
    ) -> OutputT:
        """Execute the task: render prompt, call LLM, parse & validate output.

        Args:
            input_data: Validated input matching input_schema.
            llm: Optional LangChain chat model. Falls back to get_llm().

        Returns:
            Validated output matching output_schema.

        Raises:
            ValueError: If output cannot be parsed/validated after all retries.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # Validate input
        if isinstance(input_data, self.input_schema):
            validated_input = input_data
        else:
            validated_input = self.input_schema.model_validate(input_data)

        if llm is None:
            llm = get_llm(max_tokens=8192)

        system_prompt = self.get_system_prompt()
        user_prompt = self._render_prompt(validated_input)
        raw_output = ""

        for attempt in range(1 + self.max_retries):
            try:
                if attempt == 0:
                    prompt = user_prompt
                else:
                    prompt = self._render_retry_prompt(user_prompt, raw_output, errors)

                response = await llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt),
                ])

                raw_output = response.content  # type: ignore[assignment]
                parsed = parse_llm_json(raw_output)
                output = self.output_schema.model_validate(parsed)

                # Custom validation
                if not self.validate(output):
                    errors = [
                        f"Custom validation failed for task '{self.name}'. "
                        "Review your output against the requirements."
                    ]
                    if attempt < self.max_retries:
                        logger.warning(
                            "Task '%s' custom validation failed (attempt %d/%d)",
                            self.name, attempt + 1, self.max_retries + 1,
                        )
                        continue
                    raise ValueError(
                        f"Task '{self.name}' failed custom validation after "
                        f"{self.max_retries + 1} attempts"
                    )

                logger.info(
                    "Task '%s' completed successfully on attempt %d",
                    self.name, attempt + 1,
                )
                return output

            except (json.JSONDecodeError, ValidationError) as e:
                errors = [str(e)]
                if attempt < self.max_retries:
                    logger.warning(
                        "Task '%s' output parsing/validation failed (attempt %d/%d): %s",
                        self.name, attempt + 1, self.max_retries + 1, e,
                    )
                    continue
                raise ValueError(
                    f"Task '{self.name}' failed after {self.max_retries + 1} attempts. "
                    f"Last error: {e}"
                ) from e

        # Should not reach here, but just in case
        raise ValueError(f"Task '{self.name}' failed unexpectedly")

    @abstractmethod
    def get_required_skills(self) -> list[str]:
        """Return names of skills this task depends on (for documentation)."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
