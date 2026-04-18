"""BaseWorkflow: LangGraph StateGraph wrapper for orchestrating tasks.

Workflows are the top layer of the agent architecture. They manage state,
orchestrate tasks in sequence, handle HITL interrupts and approval gates,
and persist results to the database.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict, total=False):
    """Base state shared by all workflows.

    Individual workflows extend this with their own fields.
    """

    # Core identifiers
    project_id: str

    # Task outputs — each task stores its result under its name
    task_outputs: dict[str, Any]

    # Clarification / HITL
    pending_questions: list[dict[str, Any]]
    user_responses: list[dict[str, Any]]

    # Quality gate
    quality_score: float
    quality_suggestions: list[str]
    quality_retries: int

    # Error tracking
    errors: list[str]

    # Metadata
    updated_at: str


class QualityAssessmentResult(BaseModel):
    """Standardized output from quality assessment tasks."""

    completeness: float
    depth: float
    consistency: float
    traceability: float
    actionability: float
    overall_score: float
    suggestions: list[str]


class BaseWorkflow(ABC):
    """Abstract base for all agent workflows.

    Subclasses must implement:
        build_graph() -> StateGraph
        create_initial_state(**kwargs) -> dict

    The base class provides helpers for common workflow patterns:
        - Adding task nodes that auto-store results in task_outputs
        - Quality gates with configurable thresholds
        - Approval gate creation
        - Clarification check interrupts
    """

    name: str = ""
    description: str = ""
    quality_threshold: float = 70.0
    max_quality_retries: int = 2

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Build and return the LangGraph StateGraph (do not compile)."""
        ...

    @abstractmethod
    def create_initial_state(self, **kwargs: Any) -> dict[str, Any]:
        """Create the initial state dict for this workflow."""
        ...

    def compile(self) -> Any:
        """Build and compile the graph for execution."""
        graph = self.build_graph()
        return graph.compile()

    @staticmethod
    def make_task_node(
        task_instance: Any,
        task_key: str,
        *,
        input_builder: Any | None = None,
        llm: Any | None = None,
    ) -> Any:
        """Create a graph node function that runs a task and stores its output.

        Args:
            task_instance: A BaseTask subclass instance.
            task_key: Key under which to store the result in task_outputs.
            input_builder: Optional callable(state) -> task input. If None,
                          expects state["task_outputs"] to feed into the task.
            llm: Optional LLM override.

        Returns:
            An async function suitable for StateGraph.add_node().
        """
        from datetime import datetime, timezone

        async def node_fn(state: dict[str, Any]) -> dict[str, Any]:
            try:
                if input_builder is not None:
                    task_input = input_builder(state)
                else:
                    task_input = state

                result = await task_instance.execute(task_input, llm=llm)

                task_outputs = dict(state.get("task_outputs", {}))
                task_outputs[task_key] = result.model_dump(mode="json")

                return {
                    "task_outputs": task_outputs,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as e:
                logger.error("Task '%s' failed: %s", task_key, e)
                return {
                    "errors": state.get("errors", []) + [f"Task '{task_key}' failed: {e}"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

        node_fn.__name__ = task_key
        return node_fn

    @staticmethod
    def quality_gate_router(state: dict[str, Any]) -> str:
        """Route based on quality score: 'pass', 'retry', or 'max_retries_reached'."""
        score = state.get("quality_score", 0.0)
        retries = state.get("quality_retries", 0)
        threshold = 70.0  # default, overridden in subclass logic

        if score >= threshold:
            return "pass"
        if retries >= 2:
            logger.warning(
                "Quality score %.1f below threshold after max retries", score
            )
            return "max_retries_reached"
        return "retry"

    @staticmethod
    def clarification_router(state: dict[str, Any]) -> str:
        """Route based on pending questions: 'has_questions' or 'clear'."""
        questions = state.get("pending_questions", [])
        if questions:
            return "has_questions"
        return "clear"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
