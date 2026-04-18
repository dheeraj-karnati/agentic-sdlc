"""InterpretDesignTask: loads Design artifacts and produces a PrototypeSpec."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask
from src.agents.prototype.skills.design_interpreter_skill import (
    DesignInterpreterInput,
    DesignInterpreterSkill,
    PrototypeSpec,
)


class InterpretDesignInput(BaseModel):
    design_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    business_context: list[dict[str, Any]] = Field(default_factory=list)


class InterpretDesignOutput(BaseModel):
    prototype_spec: dict[str, Any] = Field(default_factory=dict)


class InterpretDesignTask(BaseTask[InterpretDesignInput, InterpretDesignOutput]):
    """Loads Design artifacts and produces a structured PrototypeSpec."""

    name = "interpret_design"
    description = "Parse Design artifacts into pages, components, mock data, and navigation"
    input_schema = InterpretDesignInput
    output_schema = InterpretDesignOutput
    prompt_template = ""
    few_shot_examples = []

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm
        self._skill = DesignInterpreterSkill(llm=llm)

    def get_required_skills(self) -> list[str]:
        return ["design_interpreter"]

    async def execute(self, input_data: InterpretDesignInput, *, llm: Any | None = None) -> InterpretDesignOutput:
        result = await self._skill.run(
            DesignInterpreterInput(
                design_artifacts=input_data.design_artifacts,
                business_context=input_data.business_context,
            )
        )
        return InterpretDesignOutput(prototype_spec=result.model_dump(mode="json"))
