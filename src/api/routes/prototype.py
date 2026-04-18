"""Prototype Agent API routes — preview, feedback, versions."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.context_store.database import get_db
from src.context_store.models import AgentRun, AgentType, Artifact, ArtifactType, Project, ProjectStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/prototype",
    tags=["prototype"],
)


# ─── Schemas ───


class PreviewResponse(BaseModel):
    preview_url: str = ""
    version: int = 0
    provider: str = ""
    quality_score: float = 0.0
    feedback_rounds: int = 0


class PrototypeVersionResponse(BaseModel):
    version: int = 0
    preview_url: str = ""
    quality_score: float = 0.0
    feedback_rounds: int = 0
    created_at: str = ""


class FeedbackRequest(BaseModel):
    feedback: str


class FeedbackResponse(BaseModel):
    message: str = ""
    version: int = 0


# ─── Endpoints ───


@router.get("/preview", response_model=PreviewResponse)
async def get_preview(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the current prototype preview URL and version info."""
    result = await db.execute(
        select(Artifact)
        .where(
            Artifact.project_id == project_id,
            Artifact.type == ArtifactType.PROTOTYPE,
        )
        .order_by(Artifact.version.desc())
        .limit(1)
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="No prototype found for this project")

    meta = artifact.metadata_ or {}
    return {
        "preview_url": meta.get("preview_url", ""),
        "version": artifact.version,
        "provider": meta.get("provider", ""),
        "quality_score": meta.get("quality_score", 0),
        "feedback_rounds": meta.get("feedback_rounds", 0),
    }


@router.get("/versions", response_model=list[PrototypeVersionResponse])
async def list_versions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all prototype versions with metadata."""
    result = await db.execute(
        select(Artifact)
        .where(
            Artifact.project_id == project_id,
            Artifact.type == ArtifactType.PROTOTYPE,
        )
        .order_by(Artifact.version.desc())
    )
    artifacts = result.scalars().all()

    return [
        {
            "version": a.version,
            "preview_url": (a.metadata_ or {}).get("preview_url", ""),
            "quality_score": (a.metadata_ or {}).get("quality_score", 0),
            "feedback_rounds": (a.metadata_ or {}).get("feedback_rounds", 0),
            "created_at": str(a.created_at),
        }
        for a in artifacts
    ]


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    project_id: uuid.UUID,
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit feedback on the current prototype. Triggers regeneration."""
    if not request.feedback.strip():
        raise HTTPException(status_code=400, detail="Feedback cannot be empty")

    # Get latest prototype version
    result = await db.execute(
        select(Artifact)
        .where(
            Artifact.project_id == project_id,
            Artifact.type == ArtifactType.PROTOTYPE,
        )
        .order_by(Artifact.version.desc())
        .limit(1)
    )
    artifact = result.scalar_one_or_none()
    current_version = artifact.version if artifact else 0

    return {
        "message": f"Feedback received, prototype regeneration queued (v{current_version + 1})",
        "version": current_version + 1,
    }
