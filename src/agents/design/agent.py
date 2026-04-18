"""Design Agent: Workflow -> Task -> Skill architecture.

Generates comprehensive system design from Discovery phase outputs.
Produces architecture, database schema, API contracts, auth design,
and frontend components — each stored as a separate artifact.

Graph structure:
    analyze_requirements → generate_architecture → generate_data_model →
    generate_api_contracts → generate_auth_model → generate_frontend_design →
    quality_assessment → [conditional]
        ├─ pass → store_and_approve → END
        ├─ retry → generate_architecture (max 2 retries)
        └─ max_retries_reached → store_and_approve → END
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
from src.agents.design.tasks.analyze_requirements_task import (
    AnalyzeRequirementsInput,
    AnalyzeRequirementsTask,
)
from src.agents.design.tasks.design_quality_assessment_task import (
    DesignQualityAssessmentTask,
    DesignQualityInput,
)
from src.agents.design.tasks.generate_api_contracts_task import (
    GenerateAPIContractsInput,
    GenerateAPIContractsTask,
)
from src.agents.design.tasks.generate_architecture_task import (
    GenerateArchitectureInput,
    GenerateArchitectureTask,
)
from src.agents.design.tasks.generate_auth_model_task import (
    GenerateAuthModelInput,
    GenerateAuthModelTask,
)
from src.agents.design.tasks.generate_data_model_task import (
    GenerateDataModelInput,
    GenerateDataModelTask,
)
from src.agents.design.tasks.generate_frontend_design_task import (
    GenerateFrontendDesignInput,
    GenerateFrontendDesignTask,
)
from src.context_store.models import ArtifactType
from src.context_store.repository import BusinessContextRepository
from src.tools.llm import get_llm

logger = logging.getLogger(__name__)


# ─── Agent State ───


class DesignState(TypedDict, total=False):
    """State for the Design Agent workflow."""

    # Input
    project_id: str
    agent_run_id: str
    reviewer_notes: str

    # Loaded from Discovery
    business_context: list[dict[str, Any]]

    # Task outputs
    task_outputs: dict[str, Any]

    # Quality gate
    quality_score: float
    quality_suggestions: list[str]
    quality_retries: int

    # Store output
    artifacts_stored: int

    # Metadata
    errors: list[str]
    updated_at: str

    # Dependencies (injected)
    _llm: BaseChatModel | None
    _repository: BusinessContextRepository | None
    _session: object | None  # AsyncSession for storing artifacts


def create_initial_state(
    project_id: str,
    agent_run_id: str = "",
    reviewer_notes: str = "",
    llm: BaseChatModel | None = None,
    repository: BusinessContextRepository | None = None,
    session: object | None = None,
) -> DesignState:
    """Create a fresh state for the Design Agent."""
    return DesignState(
        project_id=project_id,
        agent_run_id=agent_run_id,
        reviewer_notes=reviewer_notes,
        business_context=[],
        task_outputs={},
        quality_score=0.0,
        quality_suggestions=[],
        quality_retries=0,
        artifacts_stored=0,
        errors=[],
        updated_at=datetime.now(timezone.utc).isoformat(),
        _llm=llm,
        _repository=repository,
        _session=session,
    )


# ─── Helpers ───


def _get_llm(state: DesignState) -> BaseChatModel:
    if state.get("_llm") is not None:
        return state["_llm"]  # type: ignore[return-value]
    return get_llm(max_tokens=8192)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Node Functions ───


async def load_context(state: DesignState) -> dict[str, Any]:
    """Load all business_context entries from the Discovery phase."""
    repo = state.get("_repository")
    if repo is None:
        return {
            "business_context": [],
            "errors": state.get("errors", []) + ["No repository provided"],
            "updated_at": _now(),
        }

    try:
        project_uuid = uuid.UUID(state["project_id"])
        entries = await repo.get_all_for_project(project_uuid)

        context_list = []
        for entry in entries:
            context_list.append({
                "category": entry.category,
                "title": entry.title,
                "content": entry.content,
                "metadata": entry.metadata_ or {},
            })

        return {"business_context": context_list, "updated_at": _now()}

    except Exception as e:
        logger.error("load_context failed: %s", e)
        return {
            "business_context": [],
            "errors": state.get("errors", []) + [f"load_context failed: {e}"],
            "updated_at": _now(),
        }


async def analyze_requirements(state: DesignState) -> dict[str, Any]:
    """Structure Discovery outputs for design decisions."""
    llm = _get_llm(state)
    task = AnalyzeRequirementsTask()
    context = state.get("business_context", [])

    if not context:
        return {
            "errors": state.get("errors", []) + ["No business context available"],
            "updated_at": _now(),
        }

    try:
        result = await task.execute(
            AnalyzeRequirementsInput(business_context=context), llm=llm,
        )
        task_outputs = dict(state.get("task_outputs", {}))
        task_outputs["structured_requirements"] = result.model_dump(mode="json")

        # Include reviewer notes as additional context
        if state.get("reviewer_notes"):
            reqs = task_outputs["structured_requirements"]
            reqs.setdefault("constraints", []).append(
                f"Reviewer feedback: {state['reviewer_notes']}"
            )

        return {"task_outputs": task_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("analyze_requirements failed: %s", e)
        return {
            "errors": state.get("errors", []) + [f"analyze_requirements failed: {e}"],
            "updated_at": _now(),
        }


async def generate_architecture(state: DesignState) -> dict[str, Any]:
    """Generate architecture recommendation."""
    llm = _get_llm(state)
    task = GenerateArchitectureTask(llm=llm)
    task_outputs = state.get("task_outputs", {})
    reqs = task_outputs.get("structured_requirements", {})

    try:
        result = await task.execute(
            GenerateArchitectureInput(structured_requirements=reqs), llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["architecture"] = result.architecture
        return {"task_outputs": new_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("generate_architecture failed: %s", e)
        return {
            "errors": state.get("errors", []) + [f"generate_architecture failed: {e}"],
            "updated_at": _now(),
        }


async def generate_data_model(state: DesignState) -> dict[str, Any]:
    """Generate database schema."""
    llm = _get_llm(state)
    task = GenerateDataModelTask(llm=llm)
    task_outputs = state.get("task_outputs", {})
    reqs = task_outputs.get("structured_requirements", {})

    try:
        result = await task.execute(
            GenerateDataModelInput(structured_requirements=reqs), llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["database_schema"] = result.database_schema
        return {"task_outputs": new_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("generate_data_model failed: %s", e)
        return {
            "errors": state.get("errors", []) + [f"generate_data_model failed: {e}"],
            "updated_at": _now(),
        }


async def generate_api_contracts(state: DesignState) -> dict[str, Any]:
    """Generate API specification."""
    llm = _get_llm(state)
    task = GenerateAPIContractsTask(llm=llm)
    task_outputs = state.get("task_outputs", {})
    reqs = task_outputs.get("structured_requirements", {})

    try:
        result = await task.execute(
            GenerateAPIContractsInput(structured_requirements=reqs), llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["api_specification"] = result.api_specification
        return {"task_outputs": new_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("generate_api_contracts failed: %s", e)
        return {
            "errors": state.get("errors", []) + [f"generate_api_contracts failed: {e}"],
            "updated_at": _now(),
        }


async def generate_auth_model(state: DesignState) -> dict[str, Any]:
    """Generate auth design."""
    llm = _get_llm(state)
    task = GenerateAuthModelTask(llm=llm)
    task_outputs = state.get("task_outputs", {})
    reqs = task_outputs.get("structured_requirements", {})

    try:
        result = await task.execute(
            GenerateAuthModelInput(structured_requirements=reqs), llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["auth_design"] = result.auth_design
        return {"task_outputs": new_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("generate_auth_model failed: %s", e)
        return {
            "errors": state.get("errors", []) + [f"generate_auth_model failed: {e}"],
            "updated_at": _now(),
        }


async def generate_frontend_design(state: DesignState) -> dict[str, Any]:
    """Generate frontend component architecture."""
    llm = _get_llm(state)
    task = GenerateFrontendDesignTask(llm=llm)
    task_outputs = state.get("task_outputs", {})
    reqs = task_outputs.get("structured_requirements", {})
    api = task_outputs.get("api_specification", {})

    try:
        result = await task.execute(
            GenerateFrontendDesignInput(
                structured_requirements=reqs,
                api_specification=api,
            ),
            llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["frontend_components"] = result.frontend_components
        return {"task_outputs": new_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("generate_frontend_design failed: %s", e)
        return {
            "errors": state.get("errors", []) + [f"generate_frontend_design failed: {e}"],
            "updated_at": _now(),
        }


async def quality_assessment(state: DesignState) -> dict[str, Any]:
    """Score the design quality."""
    llm = _get_llm(state)
    task = DesignQualityAssessmentTask()
    task_outputs = state.get("task_outputs", {})

    try:
        result = await task.execute(
            DesignQualityInput(
                architecture=task_outputs.get("architecture", {}),
                database_schema=task_outputs.get("database_schema", {}),
                api_specification=task_outputs.get("api_specification", {}),
                auth_design=task_outputs.get("auth_design", {}),
                frontend_components=task_outputs.get("frontend_components", {}),
                structured_requirements=task_outputs.get("structured_requirements", {}),
            ),
            llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["quality_assessment"] = result.model_dump(mode="json")
        return {
            "task_outputs": new_outputs,
            "quality_score": result.overall_score,
            "quality_suggestions": result.suggestions,
            "updated_at": _now(),
        }
    except Exception as e:
        logger.error("quality_assessment failed: %s", e)
        return {
            "quality_score": 75.0,
            "quality_suggestions": [],
            "errors": state.get("errors", []) + [f"quality_assessment failed: {e}"],
            "updated_at": _now(),
        }


async def increment_quality_retry(state: DesignState) -> dict[str, Any]:
    """Increment retry counter before looping back."""
    return {
        "quality_retries": state.get("quality_retries", 0) + 1,
        "updated_at": _now(),
    }


async def store_and_approve(state: DesignState) -> dict[str, Any]:
    """Store each design section as a separate Artifact."""
    from src.context_store.models import Artifact

    session = state.get("_session")
    task_outputs = state.get("task_outputs", {})

    if session is None:
        return {"artifacts_stored": 0, "updated_at": _now()}

    project_uuid = uuid.UUID(state["project_id"])
    run_id = uuid.UUID(state["agent_run_id"]) if state.get("agent_run_id") else None

    section_map: list[tuple[str, ArtifactType, str]] = [
        ("architecture", ArtifactType.DOCUMENT, "Architecture Recommendation"),
        ("database_schema", ArtifactType.SCHEMA, "Database Schema Design"),
        ("api_specification", ArtifactType.API_SPEC, "API Endpoint Specification"),
        ("auth_design", ArtifactType.DOCUMENT, "Authentication & Authorization Design"),
        ("frontend_components", ArtifactType.DOCUMENT, "Frontend Component Architecture"),
    ]

    stored = 0
    for section_key, artifact_type, name in section_map:
        section_data = task_outputs.get(section_key)
        if not section_data:
            continue

        try:
            artifact = Artifact(
                project_id=project_uuid,
                agent_run_id=run_id,
                type=artifact_type,
                name=name,
                content=json.dumps(section_data, indent=2),
                metadata_={
                    "section": section_key,
                    "source_agent": "design",
                    "quality_score": state.get("quality_score", 0),
                },
            )
            session.add(artifact)  # type: ignore[union-attr]
            stored += 1
        except Exception as e:
            logger.error("Failed to store artifact '%s': %s", name, e)

    try:
        await session.flush()  # type: ignore[union-attr]
    except Exception as e:
        logger.error("store_and_approve flush failed: %s", e)
        return {
            "artifacts_stored": 0,
            "errors": state.get("errors", []) + [f"store_and_approve flush failed: {e}"],
            "updated_at": _now(),
        }

    return {"artifacts_stored": stored, "updated_at": _now()}


# ─── Routing ───


def quality_gate(state: DesignState) -> str:
    """Route based on quality score."""
    score = state.get("quality_score", 0.0)
    retries = state.get("quality_retries", 0)

    if score >= 70.0:
        return "pass"
    if retries >= 2:
        logger.warning("Design quality %.1f below 70 after %d retries — proceeding", score, retries)
        return "max_retries_reached"
    return "retry"


# ─── Workflow ───


class DesignWorkflow(BaseWorkflow):
    """Design Agent workflow using the Task -> Skill architecture."""

    name = "design"
    description = "Generate comprehensive system design from Discovery outputs"
    quality_threshold = 70.0
    max_quality_retries = 2

    def build_graph(self) -> StateGraph:
        graph = StateGraph(DesignState)

        # Nodes
        graph.add_node("load_context", load_context)
        graph.add_node("analyze_requirements", analyze_requirements)
        graph.add_node("generate_architecture", generate_architecture)
        graph.add_node("generate_data_model", generate_data_model)
        graph.add_node("generate_api_contracts", generate_api_contracts)
        graph.add_node("generate_auth_model", generate_auth_model)
        graph.add_node("generate_frontend_design", generate_frontend_design)
        graph.add_node("quality_assessment", quality_assessment)
        graph.add_node("increment_quality_retry", increment_quality_retry)
        graph.add_node("store_and_approve", store_and_approve)

        # Edges: main pipeline
        graph.set_entry_point("load_context")
        graph.add_edge("load_context", "analyze_requirements")
        graph.add_edge("analyze_requirements", "generate_architecture")
        graph.add_edge("generate_architecture", "generate_data_model")
        graph.add_edge("generate_data_model", "generate_api_contracts")
        graph.add_edge("generate_api_contracts", "generate_auth_model")
        graph.add_edge("generate_auth_model", "generate_frontend_design")
        graph.add_edge("generate_frontend_design", "quality_assessment")

        # Quality gate
        graph.add_conditional_edges(
            "quality_assessment",
            quality_gate,
            {
                "pass": "store_and_approve",
                "retry": "increment_quality_retry",
                "max_retries_reached": "store_and_approve",
            },
        )

        # Retry loop
        graph.add_edge("increment_quality_retry", "generate_architecture")
        graph.add_edge("store_and_approve", END)

        return graph

    def create_initial_state(self, **kwargs: Any) -> dict[str, Any]:
        return create_initial_state(**kwargs)  # type: ignore[arg-type]


def build_design_graph() -> StateGraph:
    """Convenience function for backward compatibility."""
    workflow = DesignWorkflow()
    return workflow.build_graph()
