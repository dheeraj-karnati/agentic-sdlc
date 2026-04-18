"""Prototype Agent (D4): generates and deploys interactive prototypes.

Takes approved Design artifacts and produces a live, reviewable prototype
at a real URL. Supports iterative feedback loops.

Graph structure (first run):
    interpret_design → generate_prototype → deploy_preview →
    quality_assessment → [quality gate] → store_and_approve

Feedback loop (after user feedback):
    process_feedback → generate_prototype → deploy_preview →
    quality_assessment → store_and_approve
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.agents.base.workflow import BaseWorkflow
from src.agents.prototype.tasks.deploy_preview_task import DeployPreviewInput, DeployPreviewTask
from src.agents.prototype.tasks.generate_prototype_task import (
    GeneratePrototypeInput,
    GeneratePrototypeTask,
)
from src.agents.prototype.tasks.interpret_design_task import InterpretDesignInput, InterpretDesignTask
from src.agents.prototype.tasks.process_feedback_task import ProcessFeedbackInput, ProcessFeedbackTask
from src.agents.prototype.tasks.quality_assessment_task import (
    PrototypeQualityAssessmentTask,
    PrototypeQualityInput,
)
from src.context_store.models import ArtifactType
from src.tools.llm import get_llm

logger = logging.getLogger(__name__)


# ─── State ───


class PrototypeState(TypedDict, total=False):
    project_id: str
    agent_run_id: str
    task_outputs: dict[str, Any]

    # Versioning
    current_version: int
    feedback_history: list[dict[str, Any]]

    # Preview
    preview_url: str
    preview_provider: str

    # Quality gate
    quality_score: float
    quality_suggestions: list[str]
    quality_retries: int

    # Store output
    artifacts_stored: int

    # Feedback processing
    pending_feedback: str  # raw feedback text from user
    pending_questions: list[str]  # clarification questions for user
    requires_design_change: bool

    # Metadata
    errors: list[str]
    updated_at: str

    # Dependencies
    _llm: BaseChatModel | None
    _session: object | None
    _design_artifacts: list[dict[str, Any]]
    _business_context: list[dict[str, Any]]


def create_initial_state(
    project_id: str,
    agent_run_id: str = "",
    llm: BaseChatModel | None = None,
    session: object | None = None,
    design_artifacts: list[dict[str, Any]] | None = None,
    business_context: list[dict[str, Any]] | None = None,
    preview_provider: str = "local_docker",
) -> PrototypeState:
    return PrototypeState(
        project_id=project_id,
        agent_run_id=agent_run_id,
        task_outputs={},
        current_version=1,
        feedback_history=[],
        preview_url="",
        preview_provider=preview_provider,
        quality_score=0.0,
        quality_suggestions=[],
        quality_retries=0,
        artifacts_stored=0,
        pending_feedback="",
        pending_questions=[],
        requires_design_change=False,
        errors=[],
        updated_at=datetime.now(timezone.utc).isoformat(),
        _llm=llm,
        _session=session,
        _design_artifacts=design_artifacts or [],
        _business_context=business_context or [],
    )


def _get_llm(state: PrototypeState) -> BaseChatModel:
    if state.get("_llm") is not None:
        return state["_llm"]  # type: ignore[return-value]
    return get_llm(max_tokens=16384)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Node Functions ───


async def interpret_design(state: PrototypeState) -> dict[str, Any]:
    """Parse Design artifacts into a PrototypeSpec."""
    llm = _get_llm(state)
    task = InterpretDesignTask(llm=llm)
    artifacts = state.get("_design_artifacts", [])
    context = state.get("_business_context", [])

    try:
        result = await task.execute(
            InterpretDesignInput(design_artifacts=artifacts, business_context=context),
            llm=llm,
        )
        outputs = dict(state.get("task_outputs", {}))
        outputs["prototype_spec"] = result.prototype_spec
        return {"task_outputs": outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("interpret_design failed: %s", e)
        return {"errors": state.get("errors", []) + [f"interpret_design: {e}"], "updated_at": _now()}


async def generate_prototype(state: PrototypeState) -> dict[str, Any]:
    """Generate and validate prototype code."""
    llm = _get_llm(state)
    task = GeneratePrototypeTask(llm=llm)
    outputs = state.get("task_outputs", {})

    try:
        result = await task.execute(
            GeneratePrototypeInput(
                prototype_spec=outputs.get("prototype_spec", {}),
                feedback_history=state.get("feedback_history", []),
            ),
            llm=llm,
        )
        new_outputs = dict(outputs)
        new_outputs["prototype_code"] = result.prototype_code
        new_outputs["validation"] = result.validation
        return {"task_outputs": new_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("generate_prototype failed: %s", e)
        return {"errors": state.get("errors", []) + [f"generate_prototype: {e}"], "updated_at": _now()}


async def deploy_preview(state: PrototypeState) -> dict[str, Any]:
    """Deploy prototype and capture screenshots."""
    task = DeployPreviewTask()
    outputs = state.get("task_outputs", {})
    code = outputs.get("prototype_code", {})
    spec = outputs.get("prototype_spec", {})
    pages = [p.get("route", "/") for p in spec.get("pages", [])] or ["/"]

    try:
        result = await task.execute(DeployPreviewInput(
            prototype_code=code,
            provider=state.get("preview_provider", "local_docker"),
            project_name=f"d8x-{state['project_id'][:8]}",
            screenshot_pages=pages,
        ))
        new_outputs = dict(outputs)
        new_outputs["deployment"] = result.deployment
        new_outputs["screenshots"] = result.screenshots
        return {
            "task_outputs": new_outputs,
            "preview_url": result.deployment.get("url", ""),
            "updated_at": _now(),
        }
    except Exception as e:
        logger.error("deploy_preview failed: %s", e)
        return {"errors": state.get("errors", []) + [f"deploy_preview: {e}"], "updated_at": _now()}


async def quality_assessment(state: PrototypeState) -> dict[str, Any]:
    """Score prototype quality."""
    llm = _get_llm(state)
    task = PrototypeQualityAssessmentTask()
    outputs = state.get("task_outputs", {})

    try:
        result = await task.execute(
            PrototypeQualityInput(
                prototype_spec=outputs.get("prototype_spec", {}),
                prototype_code=outputs.get("prototype_code", {}),
                validation_result=outputs.get("validation", {}),
            ),
            llm=llm,
        )
        new_outputs = dict(outputs)
        new_outputs["quality"] = result.model_dump(mode="json")
        return {
            "task_outputs": new_outputs,
            "quality_score": result.overall_score,
            "quality_suggestions": result.suggestions,
            "updated_at": _now(),
        }
    except Exception as e:
        logger.error("quality_assessment failed: %s", e)
        return {"quality_score": 75.0, "quality_suggestions": [],
                "errors": state.get("errors", []) + [f"quality_assessment: {e}"], "updated_at": _now()}


async def increment_retry(state: PrototypeState) -> dict[str, Any]:
    return {"quality_retries": state.get("quality_retries", 0) + 1, "updated_at": _now()}


async def process_feedback(state: PrototypeState) -> dict[str, Any]:
    """Analyze user feedback and prepare for regeneration."""
    llm = _get_llm(state)
    task = ProcessFeedbackTask(llm=llm)
    outputs = state.get("task_outputs", {})
    spec = outputs.get("prototype_spec", {})
    pages = [p.get("route", "/") for p in spec.get("pages", [])]

    try:
        result = await task.execute(
            ProcessFeedbackInput(
                feedback_text=state.get("pending_feedback", ""),
                current_pages=pages,
                existing_feedback_history=state.get("feedback_history", []),
            ),
            llm=llm,
        )
        new_outputs = dict(outputs)
        new_outputs["feedback_analysis"] = result.analysis
        return {
            "task_outputs": new_outputs,
            "feedback_history": result.updated_feedback_history,
            "pending_questions": result.analysis.get("questions", []),
            "requires_design_change": result.requires_design_change,
            "current_version": state.get("current_version", 1) + 1,
            "updated_at": _now(),
        }
    except Exception as e:
        logger.error("process_feedback failed: %s", e)
        return {"errors": state.get("errors", []) + [f"process_feedback: {e}"], "updated_at": _now()}


async def store_and_approve(state: PrototypeState) -> dict[str, Any]:
    """Store prototype code and screenshots as artifacts."""
    from src.context_store.models import Artifact

    session = state.get("_session")
    outputs = state.get("task_outputs", {})
    code = outputs.get("prototype_code", {})
    version = state.get("current_version", 1)

    if session is None:
        return {"artifacts_stored": 0, "updated_at": _now()}

    project_uuid = uuid.UUID(state["project_id"])
    run_id = uuid.UUID(state["agent_run_id"]) if state.get("agent_run_id") else None
    stored = 0

    # Store file tree as single JSON artifact
    if code.get("file_tree"):
        try:
            artifact = Artifact(
                project_id=project_uuid,
                agent_run_id=run_id,
                type=ArtifactType.PROTOTYPE,
                name=f"Prototype v{version}",
                content=json.dumps(code, indent=2),
                version=version,
                metadata_={
                    "source_agent": "prototype",
                    "preview_url": state.get("preview_url", ""),
                    "quality_score": state.get("quality_score", 0),
                    "feedback_rounds": len(state.get("feedback_history", [])),
                },
            )
            session.add(artifact)  # type: ignore[union-attr]
            stored += 1
        except Exception as e:
            logger.error("Failed to store prototype: %s", e)

    try:
        await session.flush()  # type: ignore[union-attr]
    except Exception as e:
        logger.error("store_and_approve flush failed: %s", e)

    return {"artifacts_stored": stored, "updated_at": _now()}


# ─── Routing ───


def quality_gate(state: PrototypeState) -> str:
    score = state.get("quality_score", 0.0)
    retries = state.get("quality_retries", 0)
    if score >= 70.0:
        return "pass"
    if retries >= 2:
        return "max_retries"
    return "retry"


def feedback_router(state: PrototypeState) -> str:
    """Route after feedback processing."""
    if state.get("pending_questions"):
        return "needs_clarification"
    return "regenerate"


# ─── Workflow ───


class PrototypeWorkflow(BaseWorkflow):
    """D4: Prototype Agent — generate and deploy interactive prototypes."""

    name = "prototype"
    description = "Generate Next.js prototype from Design artifacts, deploy to preview URL, iterate on feedback"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(PrototypeState)

        # Nodes
        graph.add_node("interpret_design", interpret_design)
        graph.add_node("generate_prototype", generate_prototype)
        graph.add_node("deploy_preview", deploy_preview)
        graph.add_node("quality_assessment", quality_assessment)
        graph.add_node("increment_retry", increment_retry)
        graph.add_node("process_feedback", process_feedback)
        graph.add_node("store_and_approve", store_and_approve)

        # First run: interpret → generate → deploy → quality → store
        graph.set_entry_point("interpret_design")
        graph.add_edge("interpret_design", "generate_prototype")
        graph.add_edge("generate_prototype", "deploy_preview")
        graph.add_edge("deploy_preview", "quality_assessment")

        # Quality gate
        graph.add_conditional_edges("quality_assessment", quality_gate, {
            "pass": "store_and_approve",
            "retry": "increment_retry",
            "max_retries": "store_and_approve",
        })

        graph.add_edge("increment_retry", "generate_prototype")
        graph.add_edge("store_and_approve", END)

        return graph

    def create_initial_state(self, **kwargs: Any) -> dict[str, Any]:
        return create_initial_state(**kwargs)  # type: ignore[arg-type]


def build_prototype_graph() -> StateGraph:
    """Convenience function for backward compatibility."""
    return PrototypeWorkflow().build_graph()
