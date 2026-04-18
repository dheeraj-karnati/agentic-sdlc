"""Build Agent (D6): story-by-story code generation.

Placeholder workflow — compiles and runs but does not yet implement
actual code generation. Will be fleshed out in a future sprint.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.agents.base.workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class BuildState(TypedDict, total=False):
    project_id: str
    task_outputs: dict[str, Any]
    errors: list[str]
    updated_at: str


def create_initial_state(project_id: str, **kwargs: Any) -> BuildState:
    return BuildState(
        project_id=project_id,
        task_outputs={},
        errors=[],
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


async def build_stub(state: BuildState) -> dict[str, Any]:
    logger.info("Build agent stub — not yet implemented")
    return {"updated_at": datetime.now(timezone.utc).isoformat()}


class BuildWorkflow(BaseWorkflow):
    name = "build"
    description = "Story-by-story code generation and GitHub PR creation"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(BuildState)
        graph.add_node("build_stub", build_stub)
        graph.set_entry_point("build_stub")
        graph.add_edge("build_stub", END)
        return graph

    def create_initial_state(self, **kwargs: Any) -> dict[str, Any]:
        return create_initial_state(**kwargs)


def build_build_graph() -> StateGraph:
    return BuildWorkflow().build_graph()
