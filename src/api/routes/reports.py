"""Report generation routes — PDF and DOCX downloads."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services.report_generator import generate_docx_report, generate_pdf_report
from src.context_store.database import get_db
from src.context_store.models import AgentRun, Project, RunStatus

router = APIRouter(prefix="/projects/{project_id}/reports", tags=["reports"])


@router.get("/{agent_type}")
async def download_report(
    project_id: uuid.UUID,
    agent_type: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and download a PDF or DOCX report for an agent's output."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    result = await db.execute(
        select(AgentRun)
        .where(
            AgentRun.project_id == project_id,
            AgentRun.agent_type == agent_type,
            AgentRun.status.in_([RunStatus.PAUSED_FOR_APPROVAL, RunStatus.COMPLETED]),
        )
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    agent_run = result.scalar_one_or_none()
    if not agent_run:
        raise HTTPException(404, "No completed run found for this agent")

    if format == "pdf":
        content = generate_pdf_report(project, agent_run, agent_type)
        media_type = "application/pdf"
        filename = f"D8X-{agent_type}-report-{str(project_id)[:8]}.pdf"
    else:
        content = generate_docx_report(project, agent_run, agent_type)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"D8X-{agent_type}-report-{str(project_id)[:8]}.docx"

    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})
