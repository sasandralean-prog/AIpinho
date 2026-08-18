from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class WorkflowCheckpoint(AIpinhoModel):
    checkpoint_id: str = Field(default_factory=lambda: f"workflow_checkpoint_{uuid4().hex}")
    phase_id: str
    step_id: str | None = None
    checkpoint_type: str
    status: str
    event_id: str | None = None
    timestamp: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowPhaseDependency(AIpinhoModel):
    dependency_id: str = Field(default_factory=lambda: f"phase_dependency_{uuid4().hex}")
    producer_phase_id: str
    consumer_phase_id: str
    required_status: str = "completed"
    required_artifacts: list[str] = Field(default_factory=list)
    required_validations: list[str] = Field(default_factory=list)
    status: str = "pending"
    missing_reasons: list[str] = Field(default_factory=list)


class WorkflowPhase(AIpinhoModel):
    phase_id: str
    name: str
    source_step_id: str
    source_step_type: str
    action: str
    required: bool = True
    status: str = "pending"
    current_step: str | None = None
    steps: list[str] = Field(default_factory=lambda: ["START", "EXECUTION", "VALIDATION", "FINISH"])
    depends_on: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    required_validations: list[str] = Field(default_factory=list)
    required_status: str = "completed"
    produced_artifacts: list[str] = Field(default_factory=list)
    validation_refs: list[str] = Field(default_factory=list)
    validation_status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    progress: int = 0
    checkpoints: list[WorkflowCheckpoint] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class WorkflowRuntimeInstance(AIpinhoModel):
    workflow_id: str = Field(default_factory=lambda: f"workflow_{uuid4().hex}")
    task_id: str | None = None
    task_run_id: str
    operation_id: str | None = None
    runtime_profile: str | None = None
    status: str = "created"
    current_phase: str | None = None
    next_phase: str | None = None
    previous_phase: str | None = None
    current_step: str | None = None
    progress: int = 0
    phases: list[WorkflowPhase] = Field(default_factory=list)
    dependencies: list[WorkflowPhaseDependency] = Field(default_factory=list)
    checkpoints: list[WorkflowCheckpoint] = Field(default_factory=list)
    finish_contract: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    blocked_reasons: list[str] = Field(default_factory=list)


class WorkflowResumePoint(AIpinhoModel):
    workflow_id: str
    phase_id: str | None = None
    source_step_id: str | None = None
    status: str
    reason: str = ""
