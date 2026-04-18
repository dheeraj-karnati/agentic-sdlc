"""Ship Agent (D8): deploy to target environment.

Placeholder workflow — compiles and runs but does not yet implement
actual deployment. Will be fleshed out in a future sprint.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.agents.base.workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class ShipState(TypedDict, total=False):
    project_id: str
    task_outputs: dict[str, Any]
    errors: list[str]
    updated_at: str


def create_initial_state(project_id: str, **kwargs: Any) -> ShipState:
    return ShipState(
        project_id=project_id,
        task_outputs={},
        errors=[],
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


async def ship_stub(state: ShipState) -> dict[str, Any]:
    logger.info("Ship agent stub — not yet implemented")
    return {"updated_at": datetime.now(timezone.utc).isoformat()}


class ShipWorkflow(BaseWorkflow):
    name = "ship"
    description = "Deploy to target environment, monitor logs, error feedback to Build"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(ShipState)
        graph.add_node("ship_stub", ship_stub)
        graph.set_entry_point("ship_stub")
        graph.add_edge("ship_stub", END)
        return graph

    def create_initial_state(self, **kwargs: Any) -> dict[str, Any]:
        return create_initial_state(**kwargs)


def build_ship_graph() -> StateGraph:
    return ShipWorkflow().build_graph()
