"""Unit tests for the base framework: BaseSkill, BaseTask, BaseWorkflow."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from src.agents.base.skill import BaseSkill
from src.agents.base.task import BaseTask
from src.agents.base.workflow import BaseWorkflow, WorkflowState


# ─── Test Fixtures: Concrete implementations ───


class AddInput(BaseModel):
    a: int
    b: int


class AddOutput(BaseModel):
    result: int


class AddSkill(BaseSkill[AddInput, AddOutput]):
    name = "add"
    description = "Adds two numbers"
    input_model = AddInput
    output_model = AddOutput

    async def execute(self, input_data: AddInput) -> AddOutput:
        return AddOutput(result=input_data.a + input_data.b)


class FailingSkill(BaseSkill[AddInput, AddOutput]):
    """Skill that fails on first call, succeeds on second."""

    name = "failing"
    description = "Fails then succeeds"
    input_model = AddInput
    output_model = AddOutput

    def __init__(self) -> None:
        self._call_count = 0

    async def execute(self, input_data: AddInput) -> AddOutput:
        self._call_count += 1
        if self._call_count < 2:
            raise RuntimeError("Transient failure")
        return AddOutput(result=input_data.a + input_data.b)


class EchoTaskInput(BaseModel):
    message: str


class EchoTaskOutput(BaseModel):
    echo: str


class EchoTask(BaseTask[EchoTaskInput, EchoTaskOutput]):
    name = "echo"
    description = "Echoes a message"
    input_schema = EchoTaskInput
    output_schema = EchoTaskOutput
    prompt_template = "Echo this message: {message}"
    few_shot_examples = [
        {"input": {"message": "hello"}, "output": {"echo": "hello"}},
    ]

    def get_required_skills(self) -> list[str]:
        return []

    def validate(self, output: EchoTaskOutput) -> bool:
        return len(output.echo) > 0


# ─── BaseSkill tests ───


@pytest.mark.asyncio
async def test_skill_run_returns_typed_output() -> None:
    """BaseSkill.run() validates input/output and returns typed result."""
    skill = AddSkill()
    result = await skill.run(AddInput(a=2, b=3))
    assert isinstance(result, AddOutput)
    assert result.result == 5


@pytest.mark.asyncio
async def test_skill_run_validates_input() -> None:
    """BaseSkill.run() validates input against input_model."""
    skill = AddSkill()
    # Already correct type should work
    result = await skill.run(AddInput(a=10, b=20))
    assert result.result == 30


@pytest.mark.asyncio
async def test_skill_retries_on_failure() -> None:
    """BaseSkill.run() retries with exponential backoff on failure."""
    skill = FailingSkill()
    # First call fails, second succeeds — retry should handle it
    result = await skill.run(AddInput(a=1, b=1))
    assert result.result == 2
    assert skill._call_count == 2


@pytest.mark.asyncio
async def test_skill_repr() -> None:
    """BaseSkill.__repr__() includes the skill name."""
    skill = AddSkill()
    assert "add" in repr(skill)


# ─── BaseTask tests ───


def _mock_llm(content: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return llm


@pytest.mark.asyncio
async def test_task_execute_parses_llm_output() -> None:
    """BaseTask.execute() calls LLM and parses output into schema."""
    llm = _mock_llm(json.dumps({"echo": "hello world"}))
    task = EchoTask()

    result = await task.execute(EchoTaskInput(message="hello world"), llm=llm)

    assert isinstance(result, EchoTaskOutput)
    assert result.echo == "hello world"
    llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_task_retries_on_invalid_json() -> None:
    """BaseTask retries with corrective feedback on invalid JSON."""
    bad_then_good = [
        AIMessage(content="not json at all"),
        AIMessage(content=json.dumps({"echo": "fixed"})),
    ]
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=bad_then_good)
    task = EchoTask()

    result = await task.execute(EchoTaskInput(message="test"), llm=llm)

    assert result.echo == "fixed"
    assert llm.ainvoke.await_count == 2


@pytest.mark.asyncio
async def test_task_retries_on_validation_failure() -> None:
    """BaseTask retries when custom validate() returns False."""
    # First response has empty echo (fails validation), second is good
    bad_then_good = [
        AIMessage(content=json.dumps({"echo": ""})),
        AIMessage(content=json.dumps({"echo": "valid"})),
    ]
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=bad_then_good)
    task = EchoTask()

    result = await task.execute(EchoTaskInput(message="test"), llm=llm)

    assert result.echo == "valid"
    assert llm.ainvoke.await_count == 2


@pytest.mark.asyncio
async def test_task_fails_after_max_retries() -> None:
    """BaseTask raises ValueError after exhausting retries."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="not json"))
    task = EchoTask()
    task.max_retries = 1

    with pytest.raises(ValueError, match="failed after"):
        await task.execute(EchoTaskInput(message="test"), llm=llm)


@pytest.mark.asyncio
async def test_task_system_prompt_includes_schema() -> None:
    """BaseTask.get_system_prompt() includes the JSON schema."""
    task = EchoTask()
    system = task.get_system_prompt()
    assert "echo" in system
    assert "JSON" in system


@pytest.mark.asyncio
async def test_task_render_prompt_includes_examples() -> None:
    """BaseTask._render_prompt() includes few-shot examples."""
    task = EchoTask()
    rendered = task._render_prompt(EchoTaskInput(message="test"))
    assert "Example 1" in rendered
    assert "hello" in rendered


def test_task_repr() -> None:
    """BaseTask.__repr__() includes the task name."""
    task = EchoTask()
    assert "echo" in repr(task)


# ─── BaseWorkflow tests ───


def test_make_task_node_creates_callable() -> None:
    """BaseWorkflow.make_task_node() returns an async function."""
    task = EchoTask()
    node_fn = BaseWorkflow.make_task_node(task, "echo_task")
    assert callable(node_fn)
    assert node_fn.__name__ == "echo_task"


@pytest.mark.asyncio
async def test_make_task_node_stores_output() -> None:
    """make_task_node stores task output in task_outputs dict."""
    llm = _mock_llm(json.dumps({"echo": "result"}))
    task = EchoTask()

    node_fn = BaseWorkflow.make_task_node(
        task, "echo_task",
        input_builder=lambda s: EchoTaskInput(message="test"),
        llm=llm,
    )

    state: dict = {"task_outputs": {}, "errors": []}
    result = await node_fn(state)

    assert "echo_task" in result["task_outputs"]
    assert result["task_outputs"]["echo_task"]["echo"] == "result"


@pytest.mark.asyncio
async def test_make_task_node_handles_failure() -> None:
    """make_task_node adds error to errors list on failure."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))
    task = EchoTask()
    task.max_retries = 0

    node_fn = BaseWorkflow.make_task_node(
        task, "echo_task",
        input_builder=lambda s: EchoTaskInput(message="test"),
        llm=llm,
    )

    state: dict = {"task_outputs": {}, "errors": []}
    result = await node_fn(state)

    assert any("echo_task" in e for e in result.get("errors", []))


def test_quality_gate_router_pass() -> None:
    """quality_gate_router returns 'pass' when score >= threshold."""
    state = {"quality_score": 80.0, "quality_retries": 0}
    assert BaseWorkflow.quality_gate_router(state) == "pass"


def test_quality_gate_router_retry() -> None:
    """quality_gate_router returns 'retry' when score < threshold and retries available."""
    state = {"quality_score": 50.0, "quality_retries": 0}
    assert BaseWorkflow.quality_gate_router(state) == "retry"


def test_quality_gate_router_max_retries() -> None:
    """quality_gate_router returns 'max_retries_reached' after 2 retries."""
    state = {"quality_score": 50.0, "quality_retries": 2}
    assert BaseWorkflow.quality_gate_router(state) == "max_retries_reached"


def test_clarification_router_has_questions() -> None:
    state = {"pending_questions": [{"q": "test"}]}
    assert BaseWorkflow.clarification_router(state) == "has_questions"


def test_clarification_router_clear() -> None:
    state = {"pending_questions": []}
    assert BaseWorkflow.clarification_router(state) == "clear"
