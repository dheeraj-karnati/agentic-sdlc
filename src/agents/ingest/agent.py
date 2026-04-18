"""Digitize Agent (D1): ingests, parses, classifies, and structures raw inputs.

Handles all file types: documents (PDF, DOCX, XLSX), code, audio, video, images.
Produces structured content in business_context for Discovery to consume.

Graph structure:
    ingest_files → classify_and_structure → generate_inventory →
    quality_assessment → store_and_complete → END
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
from src.agents.ingest.tasks.classify_and_structure_task import (
    ClassifyAndStructureInput,
    ClassifyAndStructureTask,
    StructuredInputBundle,
)
from src.agents.ingest.tasks.generate_source_inventory_task import (
    GenerateSourceInventoryInput,
    GenerateSourceInventoryTask,
    SourceInventory,
)
from src.agents.ingest.tasks.ingest_files_task import (
    IngestFilesInput,
    IngestFilesTask,
    IngestedFiles,
    UploadedFile,
)
from src.agents.ingest.tasks.quality_and_completeness_task import (
    QualityAndCompletenessInput,
    QualityAndCompletenessTask,
)
from src.context_store.models import AgentType
from src.context_store.repository import BusinessContextRepository
from src.tools.embeddings import embed_text
from src.tools.llm import get_llm

logger = logging.getLogger(__name__)


class IngestState(TypedDict, total=False):
    project_id: str
    files: list[dict[str, str]]  # [{"filename": ..., "content": ..., "file_path": ...}]
    task_outputs: dict[str, Any]
    quality_score: float
    stored_count: int
    errors: list[str]
    updated_at: str
    _llm: BaseChatModel | None
    _repository: BusinessContextRepository | None
    _embed_fn: object | None


def create_initial_state(
    project_id: str,
    files: list[dict[str, str]] | None = None,
    llm: BaseChatModel | None = None,
    repository: BusinessContextRepository | None = None,
    embed_fn: object | None = None,
) -> IngestState:
    return IngestState(
        project_id=project_id,
        files=files or [],
        task_outputs={},
        quality_score=0.0,
        stored_count=0,
        errors=[],
        updated_at=datetime.now(timezone.utc).isoformat(),
        _llm=llm,
        _repository=repository,
        _embed_fn=embed_fn,
    )


def _get_llm(state: IngestState) -> BaseChatModel:
    if state.get("_llm") is not None:
        return state["_llm"]  # type: ignore[return-value]
    return get_llm(max_tokens=4096)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ingest_files(state: IngestState) -> dict[str, Any]:
    task = IngestFilesTask()
    uploaded = [
        UploadedFile(
            filename=f.get("filename", ""),
            content=f.get("content", ""),
            file_path=f.get("file_path", ""),
        )
        for f in state.get("files", [])
    ]

    try:
        result = await task.execute(IngestFilesInput(files=uploaded))
        outputs = dict(state.get("task_outputs", {}))
        outputs["ingested_files"] = result.model_dump(mode="json")
        return {"task_outputs": outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("ingest_files failed: %s", e)
        return {"errors": state.get("errors", []) + [f"ingest_files failed: {e}"], "updated_at": _now()}


async def classify_and_structure(state: IngestState) -> dict[str, Any]:
    llm = _get_llm(state)
    task = ClassifyAndStructureTask(llm=llm)
    outputs = state.get("task_outputs", {})
    ingested = outputs.get("ingested_files", {})

    try:
        ingested_obj = IngestedFiles.model_validate(ingested)
        result = await task.execute(ClassifyAndStructureInput(ingested_files=ingested_obj))
        new_outputs = dict(outputs)
        new_outputs["structured_bundle"] = result.model_dump(mode="json")
        return {"task_outputs": new_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("classify_and_structure failed: %s", e)
        return {"errors": state.get("errors", []) + [f"classify_and_structure failed: {e}"], "updated_at": _now()}


async def generate_inventory(state: IngestState) -> dict[str, Any]:
    task = GenerateSourceInventoryTask()
    outputs = state.get("task_outputs", {})
    bundle_data = outputs.get("structured_bundle", {})

    try:
        bundle = StructuredInputBundle.model_validate(bundle_data)
        result = await task.execute(GenerateSourceInventoryInput(structured_bundle=bundle))
        new_outputs = dict(outputs)
        new_outputs["source_inventory"] = result.model_dump(mode="json")
        return {"task_outputs": new_outputs, "updated_at": _now()}
    except Exception as e:
        logger.error("generate_inventory failed: %s", e)
        return {"errors": state.get("errors", []) + [f"generate_inventory failed: {e}"], "updated_at": _now()}


async def quality_assessment(state: IngestState) -> dict[str, Any]:
    task = QualityAndCompletenessTask()
    outputs = state.get("task_outputs", {})
    inventory_data = outputs.get("source_inventory", {})

    try:
        inventory = SourceInventory.model_validate(inventory_data)
        result = await task.execute(QualityAndCompletenessInput(source_inventory=inventory))
        new_outputs = dict(outputs)
        new_outputs["quality_report"] = result.model_dump(mode="json")
        return {
            "task_outputs": new_outputs,
            "quality_score": result.overall_score,
            "updated_at": _now(),
        }
    except Exception as e:
        logger.error("quality_assessment failed: %s", e)
        return {
            "quality_score": 50.0,
            "errors": state.get("errors", []) + [f"quality_assessment failed: {e}"],
            "updated_at": _now(),
        }


async def store_and_complete(state: IngestState) -> dict[str, Any]:
    """Store all digitized sources in business_context with embeddings."""
    repo = state.get("_repository")
    efn = state.get("_embed_fn", embed_text)
    project_uuid = uuid.UUID(state["project_id"])
    stored = 0

    outputs = state.get("task_outputs", {})
    bundle_data = outputs.get("structured_bundle", {})
    sources = bundle_data.get("sources", [])

    for src in sources:
        title = src.get("original_filename", "untitled")
        text = src.get("text", "")
        if not text:
            continue

        embedding = None
        try:
            if efn is not None:
                embedding = await efn(text[:2000])  # type: ignore[misc]
        except Exception:
            pass

        metadata = {
            "source_id": src.get("source_id", ""),
            "content_type": src.get("content_type", ""),
            "input_type": src.get("input_type", ""),
            "key_topics": src.get("key_topics", []),
            "quality_score": state.get("quality_score", 0),
        }

        if repo is not None:
            try:
                await repo.store_context(
                    project_id=project_uuid,
                    category="ingested_source",
                    title=title,
                    content=text,
                    embedding=embedding,
                    source_agent=AgentType.INGEST,
                    metadata=metadata,
                )
                stored += 1
            except Exception as e:
                logger.error("Failed to store source '%s': %s", title, e)

    return {"stored_count": stored, "updated_at": _now()}


class IngestWorkflow(BaseWorkflow):
    """D1: Digitize Agent — ingest, parse, classify, and store raw inputs."""

    name = "ingest"
    description = "Ingest and parse raw inputs (docs, code, audio, video, images) into structured content"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(IngestState)

        graph.add_node("ingest_files", ingest_files)
        graph.add_node("classify_and_structure", classify_and_structure)
        graph.add_node("generate_inventory", generate_inventory)
        graph.add_node("quality_assessment", quality_assessment)
        graph.add_node("store_and_complete", store_and_complete)

        graph.set_entry_point("ingest_files")
        graph.add_edge("ingest_files", "classify_and_structure")
        graph.add_edge("classify_and_structure", "generate_inventory")
        graph.add_edge("generate_inventory", "quality_assessment")
        graph.add_edge("quality_assessment", "store_and_complete")
        graph.add_edge("store_and_complete", END)

        return graph

    def create_initial_state(self, **kwargs: Any) -> dict[str, Any]:
        return create_initial_state(**kwargs)  # type: ignore[arg-type]


def build_ingest_graph() -> StateGraph:
    """Convenience function."""
    return IngestWorkflow().build_graph()
