"""
Approval gate logic for the SDLC pipeline.

Provides functions to:
1. Create an approval_gates record when an agent completes
2. Transition the agent_run status to paused_for_approval
3. Process approval decisions (approve / reject / request revision)
4. Advance the project to the next phase on approval
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.context_store.models import (
    AgentRun,
    AgentType,
    ApprovalGate,
    ApprovalStatus,
    Project,
    ProjectStatus,
    RunStatus,
)

# D8 Flow: Maps each agent type to the next project status after approval
PHASE_TRANSITIONS: dict[AgentType, ProjectStatus] = {
    AgentType.INGEST: ProjectStatus.DISCOVER,
    AgentType.DISCOVER: ProjectStatus.DESIGN,
    AgentType.DESIGN: ProjectStatus.PROTOTYPE,
    AgentType.PROTOTYPE: ProjectStatus.PLAN,
    AgentType.PLAN: ProjectStatus.BUILD,
    AgentType.BUILD: ProjectStatus.TEST,
    AgentType.TEST: ProjectStatus.SHIP,
    AgentType.SHIP: ProjectStatus.COMPLETED,
}

# Maps each agent type to the project status representing that phase
PHASE_STATUS: dict[AgentType, ProjectStatus] = {
    AgentType.INGEST: ProjectStatus.INGEST,
    AgentType.DISCOVER: ProjectStatus.DISCOVER,
    AgentType.DESIGN: ProjectStatus.DESIGN,
    AgentType.PROTOTYPE: ProjectStatus.PROTOTYPE,
    AgentType.PLAN: ProjectStatus.PLAN,
    AgentType.BUILD: ProjectStatus.BUILD,
    AgentType.TEST: ProjectStatus.TEST,
    AgentType.SHIP: ProjectStatus.SHIP,
}


async def create_approval_gate(
    session: AsyncSession,
    agent_run: AgentRun,
) -> ApprovalGate:
    """Create a pending approval gate for a completed agent run.

    Also transitions the agent_run status to paused_for_approval.
    """
    agent_run.status = RunStatus.PAUSED_FOR_APPROVAL

    gate_name = f"{agent_run.agent_type.value}_approval"
    gate = ApprovalGate(
        project_id=agent_run.project_id,
        agent_run_id=agent_run.id,
        gate_name=gate_name,
        status=ApprovalStatus.PENDING,
    )
    session.add(gate)
    await session.flush()
    await session.refresh(gate)
    return gate


async def process_decision(
    session: AsyncSession,
    gate: ApprovalGate,
    decision: ApprovalStatus,
    reviewer_notes: str | None = None,
) -> ApprovalGate:
    """Process a reviewer's decision on an approval gate.

    - approved: advances project to the next SDLC phase, marks run completed
    - rejected: marks the agent run as failed
    - revision_requested: marks the agent run as failed so it can be re-triggered
    """
    gate.status = decision
    gate.reviewer_notes = reviewer_notes
    gate.decided_at = datetime.now(timezone.utc)

    # Fetch the associated agent run
    result = await session.execute(
        select(AgentRun).where(AgentRun.id == gate.agent_run_id)
    )
    agent_run = result.scalar_one()

    # Fetch the project
    result = await session.execute(
        select(Project).where(Project.id == gate.project_id)
    )
    project = result.scalar_one()

    if decision == ApprovalStatus.APPROVED:
        agent_run.status = RunStatus.COMPLETED
        agent_run.completed_at = datetime.now(timezone.utc)
        next_status = PHASE_TRANSITIONS.get(agent_run.agent_type)
        if next_status:
            project.status = next_status

    elif decision == ApprovalStatus.REJECTED:
        agent_run.status = RunStatus.FAILED
        agent_run.error_details = f"Rejected: {reviewer_notes or 'No reason given'}"

    elif decision == ApprovalStatus.REVISION_REQUESTED:
        agent_run.status = RunStatus.FAILED
        agent_run.error_details = f"Revision requested: {reviewer_notes or 'No details'}"

    await session.flush()
    await session.refresh(gate)
    return gate