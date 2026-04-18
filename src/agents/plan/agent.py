"""
Define Agent: decomposes an approved prototype design into epics and user stories.

Artifact-first approach: generates the full plan (epics + nested stories) in a
single LLM call, stores it as a JSON artifact for human review, and imports
to DB tables only after approval.

Graph structure:
    gather_context ──▶ generate_plan ──▶ validate_plan ──▶ store_artifact ──▶ END
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.context_store.models import ArtifactType
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


# ─── Prompts ───


PLAN_SYSTEM_PROMPT = """\
You are an expert product manager and software architect. Given the system \
design and prototype for a modernised application, decompose the work into \
**epics** and **user stories**.

Return a single JSON object with this exact structure:
{
  "epics": [
    {
      "title": "Epic title",
      "description": "What this epic covers",
      "priority": 1,
      "stories": [
        {
          "title": "Story title",
          "description": "As a [role], I want [feature], so that [benefit]",
          "acceptance_criteria": ["Given...", "When...", "Then..."],
          "story_points": 3,
          "priority": 1,
          "technical_notes": "Implementation approach...",
          "schema_changes": "ALTER TABLE... or null",
          "api_endpoints": [{"method": "POST", "path": "/api/...", "description": "..."}],
          "ui_components": [{"name": "ComponentName", "purpose": "..."}],
          "dependencies": ["Other story title this depends on"]
        }
      ]
    }
  ]
}

Guidelines:
- Aim for 4-8 epics covering the full project scope
- Order epics by recommended implementation sequence
- Each epic should have 2-6 user stories
- Story descriptions must follow: "As a [role], I want [feature], so that [benefit]"
- Story points use Fibonacci: 1, 2, 3, 5, 8, 13
- Dependencies reference story titles within or across epics
- Include specific acceptance criteria for each story
- Include technical_notes about implementation approach
- List schema_changes if database changes are needed (null if none)
- List api_endpoints as objects with method, path, description
- List ui_components as objects with name, purpose"""


# ─── Agent State ───


class PlanState(TypedDict):
    """State for the Define Agent graph."""

    # Input
    project_id: str
    agent_run_id: str
    reviewer_notes: str

    # Loaded context
    design_artifacts: list[dict]
    prototype_artifacts: list[dict]
    business_context: list[dict]

    # Generated plan (single artifact)
    plan: dict  # {"epics": [{"title":..., "stories": [...]}]}
    validation_issues: list[str]

    # Artifact output
    plan_artifact_id: str | None

    # Metadata
    errors: list[str]
    updated_at: str

    # Dependencies (injected, not serialized)
    _llm: BaseChatModel | None
    _session: object | None


def create_initial_state(
    project_id: str,
    agent_run_id: str = "",
    reviewer_notes: str = "",
    llm: BaseChatModel | None = None,
    session: object | None = None,
) -> PlanState:
    """Create a fresh state for the Define Agent."""
    return PlanState(
        project_id=project_id,
        agent_run_id=agent_run_id,
        reviewer_notes=reviewer_notes,
        design_artifacts=[],
        prototype_artifacts=[],
        business_context=[],
        plan={},
        validation_issues=[],
        plan_artifact_id=None,
        errors=[],
        updated_at=datetime.now(timezone.utc).isoformat(),
        _llm=llm,
        _session=session,
    )


# ─── Helpers ───


def _get_llm(state: PlanState) -> BaseChatModel:
    """Return the injected LLM or create a default one via centralized factory."""
    if state.get("_llm") is not None:
        return state["_llm"]  # type: ignore[return-value]
    return get_llm(max_tokens=16384)


def _format_context(
    design_artifacts: list[dict],
    prototype_artifacts: list[dict],
    business_context: list[dict],
) -> str:
    """Format all context into readable text for the LLM."""
    parts: list[str] = []

    if design_artifacts:
        parts.append("# Design Artifacts\n")
        for art in design_artifacts:
            content = art.get("content", "")
            try:
                parsed = json.loads(content)
                content = json.dumps(parsed, indent=2)
            except (json.JSONDecodeError, TypeError):
                pass
            parts.append(f"## {art.get('name', 'Untitled')}\n\n{content}")

    if prototype_artifacts:
        parts.append("\n# Prototype Artifacts\n")
        for art in prototype_artifacts:
            parts.append(f"## {art.get('name', 'Untitled')}\n\n{art.get('content', '')}")

    if business_context:
        parts.append("\n# Business Context\n")
        for ctx in business_context:
            parts.append(f"## {ctx.get('title', ctx.get('category', 'Context'))}\n\n{ctx.get('content', '')}")

    return "\n\n---\n\n".join(parts)


def topological_sort_stories(plan: dict) -> list[dict]:
    """Flatten and topologically sort all stories across epics.

    Returns a flat list of story dicts, each tagged with 'epic_title'
    and assigned a global 'sequence_order'.
    """
    all_stories: list[dict] = []
    for epic in plan.get("epics", []):
        for story in epic.get("stories", []):
            story_copy = dict(story)
            story_copy["epic_title"] = epic["title"]
            all_stories.append(story_copy)

    if not all_stories:
        return []

    # Build title → story lookup
    by_title: dict[str, dict] = {}
    for s in all_stories:
        by_title[s["title"]] = s

    # Topological sort by dependencies
    ordered: list[dict] = []
    visited: set[str] = set()

    def visit(story: dict) -> None:
        title = story["title"]
        if title in visited:
            return
        visited.add(title)
        for dep_title in story.get("dependencies", []):
            dep = by_title.get(dep_title)
            if dep:
                visit(dep)
        ordered.append(story)

    # Sort by priority first so topo-sort preserves priority order
    for s in sorted(all_stories, key=lambda x: x.get("priority", 999)):
        visit(s)

    # Assign global sequence_order
    for i, story in enumerate(ordered):
        story["sequence_order"] = i + 1

    return ordered


# ─── Node Functions ───


async def gather_context(state: PlanState) -> dict:
    """Load design artifacts, prototype artifacts, and business context."""
    from sqlalchemy import select

    from src.context_store.models import Artifact, BusinessContext

    session = state.get("_session")
    if session is None:
        return {
            "errors": state.get("errors", []) + ["No database session provided"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        project_uuid = uuid.UUID(state["project_id"])

        # Load design artifacts
        result = await session.execute(  # type: ignore[union-attr]
            select(Artifact)
            .where(
                Artifact.project_id == project_uuid,
                Artifact.metadata_["source_agent"].astext == "design",
            )
            .order_by(Artifact.created_at)
        )
        design_arts = [
            {
                "name": a.name,
                "type": a.type.value if hasattr(a.type, "value") else str(a.type),
                "content": a.content or "",
                "metadata": a.metadata_ or {},
            }
            for a in result.scalars().all()
        ]

        # Load prototype artifacts (latest version)
        result = await session.execute(  # type: ignore[union-attr]
            select(Artifact)
            .where(
                Artifact.project_id == project_uuid,
                Artifact.metadata_["source_agent"].astext == "prototype",
            )
            .order_by(Artifact.version.desc(), Artifact.created_at.desc())
        )
        proto_arts = [
            {
                "name": a.name,
                "content": a.content or "",
                "metadata": a.metadata_ or {},
            }
            for a in result.scalars().all()
        ]

        # Load business context
        result = await session.execute(  # type: ignore[union-attr]
            select(BusinessContext)
            .where(BusinessContext.project_id == project_uuid)
            .order_by(BusinessContext.created_at)
        )
        biz_ctx = [
            {
                "category": bc.category,
                "title": bc.title,
                "content": bc.content,
            }
            for bc in result.scalars().all()
        ]

        return {
            "design_artifacts": design_arts,
            "prototype_artifacts": proto_arts,
            "business_context": biz_ctx,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return {
            "errors": state.get("errors", []) + [f"gather_context failed: {e}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


async def generate_plan(state: PlanState) -> dict:
    """Generate the full plan (epics + nested stories) in a single LLM call."""
    design_arts = state.get("design_artifacts", [])
    proto_arts = state.get("prototype_artifacts", [])
    biz_ctx = state.get("business_context", [])

    if not design_arts and not proto_arts:
        return {
            "plan": {},
            "errors": state.get("errors", []) + ["No design or prototype artifacts available"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    llm = _get_llm(state)
    context_text = _format_context(design_arts, proto_arts, biz_ctx)

    extra = ""
    if state.get("reviewer_notes"):
        extra = f"\n\n--- Reviewer Feedback ---\n{state['reviewer_notes']}"

    try:
        response = await llm.ainvoke([
            SystemMessage(content=PLAN_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Generate the full implementation plan for this project:\n\n{context_text}{extra}"
            ),
        ])

        parsed = parse_llm_json(response.content)

        # Normalize to {"epics": [...]} structure
        if isinstance(parsed, list):
            # LLM returned a bare array of epics
            plan = {"epics": parsed}
        elif isinstance(parsed, dict):
            if "epics" in parsed and isinstance(parsed["epics"], list):
                plan = parsed
            else:
                # Try common wrapper keys
                for key in ("data", "items", "results", "plan"):
                    if key in parsed and isinstance(parsed[key], list):
                        plan = {"epics": parsed[key]}
                        break
                else:
                    # Single epic as dict — wrap
                    plan = {"epics": [parsed]}
        else:
            plan = {"epics": []}

        # Ensure each epic has a stories array and sequence_order
        for i, epic in enumerate(plan.get("epics", [])):
            epic.setdefault("stories", [])
            epic["sequence_order"] = i + 1
            # Ensure each story has required fields
            for j, story in enumerate(epic["stories"]):
                story.setdefault("acceptance_criteria", [])
                story.setdefault("dependencies", [])
                story.setdefault("api_endpoints", [])
                story.setdefault("ui_components", [])

    except Exception as e:
        return {
            "plan": {},
            "errors": state.get("errors", []) + [f"generate_plan failed: {e}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "plan": plan,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def validate_plan(state: PlanState) -> dict:
    """Validate the generated plan for completeness and consistency."""
    issues: list[str] = []
    plan = state.get("plan", {})
    epics = plan.get("epics", [])

    if not epics:
        issues.append("No epics were generated")
        return {
            "validation_issues": issues,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Collect all story titles across all epics
    all_story_titles: set[str] = set()
    for epic in epics:
        stories = epic.get("stories", [])
        if not stories:
            issues.append(f"Epic '{epic['title']}' has no user stories")
        for story in stories:
            all_story_titles.add(story["title"])

    # Check dependency references are valid
    for epic in epics:
        for story in epic.get("stories", []):
            for dep in story.get("dependencies", []):
                if dep not in all_story_titles:
                    issues.append(
                        f"Story '{story['title']}' depends on '{dep}' which doesn't exist"
                    )

    return {
        "validation_issues": issues,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def store_artifact(state: PlanState) -> dict:
    """Store the plan as a versioned JSON artifact for human review.

    Does NOT write to epics/user_stories tables — that happens via the
    import endpoint after approval.
    """
    from src.context_store.models import Artifact

    session = state.get("_session")
    if session is None:
        return {
            "errors": state.get("errors", []) + ["No database session for store_artifact"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    plan = state.get("plan", {})
    if not plan.get("epics"):
        return {
            "errors": state.get("errors", []) + ["No plan to store"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    project_uuid = uuid.UUID(state["project_id"])
    run_id = uuid.UUID(state["agent_run_id"]) if state.get("agent_run_id") else None

    # Add metadata to the plan artifact
    plan_with_meta = {
        **plan,
        "validation_issues": state.get("validation_issues", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        artifact = Artifact(
            project_id=project_uuid,
            agent_run_id=run_id,
            type=ArtifactType.PLAN,
            name="Implementation Plan",
            content=json.dumps(plan_with_meta, indent=2),
            version=1,
            metadata_={"source_agent": "define"},
        )
        session.add(artifact)  # type: ignore[union-attr]
        await session.flush()  # type: ignore[union-attr]
        await session.refresh(artifact)  # type: ignore[union-attr]

        return {
            "plan_artifact_id": str(artifact.id),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return {
            "errors": state.get("errors", []) + [f"store_artifact failed: {e}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


# ─── Import (called from route after approval) ───


async def import_plan_to_db(
    session: object,
    project_id: uuid.UUID,
    agent_run_id: uuid.UUID | None,
    plan: dict,
) -> dict[str, int]:
    """Import a plan artifact's epics and stories into the database tables.

    Called from the import endpoint after the plan has been reviewed and approved.
    Returns counts of epics and stories stored.
    """
    from src.context_store.models import Epic, EpicStatus, StoryStatus, UserStory

    epics_data = plan.get("epics", [])
    if not epics_data:
        return {"epics_stored": 0, "stories_stored": 0}

    # Flatten and sort stories for global sequencing
    sorted_stories = topological_sort_stories(plan)

    # Create epic records and map title → Epic for story FK
    epic_map: dict[str, object] = {}
    epics_stored = 0

    for i, epic_data in enumerate(epics_data):
        epic = Epic(
            project_id=project_id,
            agent_run_id=agent_run_id,
            title=epic_data["title"],
            description=epic_data.get("description"),
            priority=epic_data.get("priority", 0),
            sequence_order=epic_data.get("sequence_order", i + 1),
            status=EpicStatus.DRAFT,
            metadata_={"source_agent": "define"},
        )
        session.add(epic)  # type: ignore[union-attr]
        epic_map[epic_data["title"]] = epic
        epics_stored += 1

    await session.flush()  # type: ignore[union-attr]

    # Create story records using topologically sorted order
    stories_stored = 0
    for story_data in sorted_stories:
        epic_title = story_data.get("epic_title", "")
        epic = epic_map.get(epic_title)
        if not epic:
            continue

        story = UserStory(
            epic_id=epic.id,  # type: ignore[union-attr]
            project_id=project_id,
            title=story_data["title"],
            description=story_data.get("description"),
            acceptance_criteria=story_data.get("acceptance_criteria", []),
            story_points=story_data.get("story_points"),
            priority=story_data.get("priority", 0),
            sequence_order=story_data.get("sequence_order", 0),
            status=StoryStatus.DRAFT,
            technical_notes=story_data.get("technical_notes"),
            schema_changes=story_data.get("schema_changes"),
            api_endpoints=story_data.get("api_endpoints", []),
            ui_components=story_data.get("ui_components", []),
            dependencies=story_data.get("dependencies", []),
            metadata_={"source_agent": "define"},
        )
        session.add(story)  # type: ignore[union-attr]
        stories_stored += 1

    await session.flush()  # type: ignore[union-attr]

    return {"epics_stored": epics_stored, "stories_stored": stories_stored}


# ─── Build Graph ───


def build_plan_graph() -> StateGraph:
    """Build the Define Agent LangGraph StateGraph.

    Graph:
        gather_context ──▶ generate_plan ──▶ validate_plan ──▶ store_artifact ──▶ END
    """
    graph = StateGraph(PlanState)

    # Nodes
    graph.add_node("gather_context", gather_context)
    graph.add_node("generate_plan", generate_plan)
    graph.add_node("validate_plan", validate_plan)
    graph.add_node("store_artifact", store_artifact)

    # Edges — linear pipeline
    graph.set_entry_point("gather_context")
    graph.add_edge("gather_context", "generate_plan")
    graph.add_edge("generate_plan", "validate_plan")
    graph.add_edge("validate_plan", "store_artifact")
    graph.add_edge("store_artifact", END)

    return graph
