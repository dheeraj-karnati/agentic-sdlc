"""Project CRUD API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from src.context_store.database import get_db
from src.context_store.models import AgentRun, Artifact, Project

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Create a new modernization project."""
    project = Project(
        name=payload.name,
        description=payload.description,
        config=payload.config,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all projects with pagination."""
    count_result = await db.execute(select(func.count(Project.id)))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit)
    )
    projects = list(result.scalars().all())

    return {"projects": projects, "total": total}


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Get a single project by ID."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Update a project's details."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)


@router.get("/{project_id}/runs")
async def list_runs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all agent runs for a project, newest first."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(AgentRun.created_at.desc())
    )
    runs = list(result.scalars().all())
    return [
        {
            "id": str(r.id),
            "agent_type": r.agent_type.value if r.agent_type else None,
            "status": r.status.value if r.status else None,
            "output_summary": r.output_summary or {},
            "error_details": r.error_details,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.get("/{project_id}/artifacts")
async def list_artifacts(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all artifacts for a project."""
    result = await db.execute(
        select(Artifact)
        .where(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
    )
    artifacts = list(result.scalars().all())
    return [
        {
            "id": str(a.id),
            "project_id": str(a.project_id),
            "agent_run_id": str(a.agent_run_id) if a.agent_run_id else None,
            "type": a.type.value if a.type else None,
            "name": a.name,
            "content": a.content,
            "version": a.version,
            "metadata": a.metadata_ or {},
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in artifacts
    ]
