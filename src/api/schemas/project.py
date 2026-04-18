"""Pydantic schemas for API request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.context_store.models import AgentType, ApprovalStatus, EpicStatus, ProjectStatus, RunStatus, StoryStatus


# ─── Project Schemas ───


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    config: dict = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None
    config: dict | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    config: dict
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


# ─── Agent Run Schemas ───


class AgentRunCreate(BaseModel):
    agent_type: AgentType
    input_context: dict = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    agent_type: AgentType
    status: RunStatus
    input_context: dict
    output_summary: dict
    error_details: str | None
    token_usage: dict
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# ─── Approval Schemas ───


class ApprovalDecision(BaseModel):
    status: ApprovalStatus = Field(
        ..., description="Must be approved, rejected, or revision_requested"
    )
    reviewer_notes: str | None = None


class ApprovalGateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    agent_run_id: uuid.UUID
    status: ApprovalStatus
    reviewer_notes: str | None
    decided_at: datetime | None
    created_at: datetime


class ApprovalGateDetailResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    agent_run_id: uuid.UUID
    status: ApprovalStatus
    reviewer_notes: str | None
    decided_at: datetime | None
    created_at: datetime
    agent_type: AgentType
    run_status: RunStatus
    output_summary: dict = Field(default_factory=dict)


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalGateResponse]
    total: int


class ApprovalDecideResponse(BaseModel):
    id: uuid.UUID
    status: ApprovalStatus
    project_status: ProjectStatus
    message: str


# ─── Conversation Schemas ───


class ConversationMessageCreate(BaseModel):
    message: str = Field(..., min_length=1)
    structured_data: dict | None = None


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    agent_run_id: uuid.UUID | None
    direction: str
    message: str
    structured_data: dict | None
    created_at: datetime


# ─── Discovery Agent Schemas ───


class DiscoveryStartRequest(BaseModel):
    document_text: str = Field(default="", description="Raw text content to analyze (optional for simulation)")


class DiscoveryStartResponse(BaseModel):
    run_id: uuid.UUID
    status: RunStatus
    message: str


class ClarificationQuestion(BaseModel):
    finding_title: str
    question: str
    reason: str


class AgentStatusResponse(BaseModel):
    run_id: uuid.UUID
    agent_type: AgentType
    status: RunStatus
    pending_questions: list[ClarificationQuestion] = Field(default_factory=list)
    output_summary: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class UserAnswer(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class RespondRequest(BaseModel):
    answers: list[UserAnswer] = Field(..., min_length=1)


class RespondResponse(BaseModel):
    run_id: uuid.UUID
    status: RunStatus
    message: str


# ─── Design Agent Schemas ───


class DesignStartRequest(BaseModel):
    reviewer_notes: str | None = Field(
        None, description="Optional reviewer feedback to address in this design run"
    )


class DesignStartResponse(BaseModel):
    run_id: uuid.UUID
    status: RunStatus
    message: str


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    agent_run_id: uuid.UUID | None
    type: str
    name: str
    content: str | None
    version: int
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class DesignOutputResponse(BaseModel):
    run_id: uuid.UUID
    agent_type: AgentType
    status: RunStatus
    design: dict = Field(default_factory=dict)
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ─── Demo Agent Schemas ───


class PrototypeStartRequest(BaseModel):
    reviewer_notes: str | None = Field(
        None, description="Optional reviewer feedback to address in this demo run"
    )


class PrototypeStartResponse(BaseModel):
    run_id: uuid.UUID
    status: RunStatus
    message: str


class PrototypeComponentManifest(BaseModel):
    name: str
    purpose: str
    workflows: list[str] = Field(default_factory=list)


class PrototypeOutputResponse(BaseModel):
    run_id: uuid.UUID
    agent_type: AgentType
    status: RunStatus
    prototype: dict = Field(default_factory=dict)
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PrototypeFeedbackRequest(BaseModel):
    feedback: str = Field(..., min_length=1, description="Freeform feedback on the demo")


class PrototypeFeedbackResponse(BaseModel):
    run_id: uuid.UUID
    status: RunStatus
    message: str
    version: int = Field(..., description="Version number of the new demo iteration")


# ─── Define Agent Schemas ───


class PlanStartRequest(BaseModel):
    reviewer_notes: str | None = Field(
        None, description="Optional reviewer feedback to address in this define run"
    )


class PlanStartResponse(BaseModel):
    run_id: uuid.UUID
    status: RunStatus
    message: str


class EpicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    agent_run_id: uuid.UUID | None
    title: str
    description: str | None
    priority: int
    sequence_order: int
    status: EpicStatus
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class EpicUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: int | None = None
    sequence_order: int | None = None
    status: EpicStatus | None = None


class UserStoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    epic_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    acceptance_criteria: list = Field(default_factory=list)
    story_points: int | None
    priority: int
    sequence_order: int
    status: StoryStatus
    technical_notes: str | None
    schema_changes: str | None
    api_endpoints: list = Field(default_factory=list)
    ui_components: list = Field(default_factory=list)
    dependencies: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class UserStoryCreate(BaseModel):
    epic_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, description="As a... I want... So that...")
    acceptance_criteria: list[str] = Field(default_factory=list)
    story_points: int | None = Field(None, ge=1, le=100)
    priority: int = Field(default=0, ge=0)


class UserStoryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    acceptance_criteria: list[str] | None = None
    story_points: int | None = Field(None, ge=1, le=100)
    priority: int | None = Field(None, ge=0)
    sequence_order: int | None = None
    status: StoryStatus | None = None
    technical_notes: str | None = None
    schema_changes: str | None = None
    api_endpoints: list | None = None
    ui_components: list | None = None
    dependencies: list | None = None


class ResequenceItem(BaseModel):
    id: uuid.UUID
    sequence_order: int = Field(..., ge=0)


class ResequenceRequest(BaseModel):
    stories: list[ResequenceItem] = Field(..., min_length=1)


class PlanOutputResponse(BaseModel):
    run_id: uuid.UUID
    agent_type: AgentType
    status: RunStatus
    epics: list[EpicResponse] = Field(default_factory=list)
    stories: list[UserStoryResponse] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PlanArtifactResponse(BaseModel):
    artifact_id: uuid.UUID
    run_id: uuid.UUID
    plan: dict = Field(default_factory=dict)
    version: int
    created_at: datetime


class PlanImportResponse(BaseModel):
    run_id: uuid.UUID
    epics_imported: int
    stories_imported: int
    message: str


# ─── Health Check ───


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    environment: str
