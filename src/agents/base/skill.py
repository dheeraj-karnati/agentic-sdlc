"""BaseSkill: stateless, reusable, independently testable capability.

Skills are the lowest-level building block in the agent architecture.
Each skill does ONE thing well and is defined by typed input/output models.
Skills never call the database or manage state.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseSkill(ABC, Generic[InputT, OutputT]):
    """Abstract base for all skills.

    Subclasses must define:
        name:         short identifier (e.g. "code_analysis")
        description:  what the skill does
        input_model:  Pydantic model class for input validation
        output_model: Pydantic model class for output validation

    And implement:
        execute(input_data) -> OutputT
    """

    name: str = ""
    description: str = ""
    input_model: type[InputT]  # type: ignore[assignment]
    output_model: type[OutputT]  # type: ignore[assignment]

    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """Run the skill on validated input and return typed output."""
        ...

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def run(self, input_data: InputT) -> OutputT:
        """Validate input, execute with retry, validate output.

        This is the public entry point. It wraps execute() with:
        - Input validation via the Pydantic input_model
        - Tenacity retry (3 attempts, exponential backoff)
        - Output type checking
        """
        # Validate input — if it's already the right type, re-validate
        if isinstance(input_data, self.input_model):
            validated_input = input_data
        else:
            validated_input = self.input_model.model_validate(input_data)

        logger.debug("Skill '%s' executing (attempt will retry on failure)", self.name)
        result = await self.execute(validated_input)

        if not isinstance(result, self.output_model):
            raise TypeError(
                f"Skill '{self.name}' returned {type(result).__name__}, "
                f"expected {self.output_model.__name__}"
            )
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
