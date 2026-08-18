from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


UniversalTaskStatus = Literal[
    "CREATED",
    "QUEUED",
    "WAITING_DELEGATION",
    "WAITING_APPROVAL",
    "WAITING_USER",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "BLOCKED",
    "CANCELLED",
    "TIMEOUT",
]


class UniversalTaskProgress(AIpinhoModel):
    percent: int = 0
    completed_units: int = 0
    total_units: int = 0
    basis: str = "task_run_plan_steps"
    is_estimated: bool = False


class UniversalTaskApprovalState(AIpinhoModel):
    status: str = "none"
    approval_id: str | None = None
    required_actions: list[str] = Field(default_factory=list)
    risk_level: str | None = None
    expires_at: str | None = None
    decided_at: str | None = None
    source: str = "task_run"


class UniversalTaskValidationState(AIpinhoModel):
    status: str = "not_started"
    validation_id: str | None = None
    safe_to_report_success: bool = False
    missing_outputs: list[str] = Field(default_factory=list)
    summary: str | None = None
    source: str = "task_run_result"


class UniversalTaskArtifactState(AIpinhoModel):
    status: str = "none"
    count: int = 0
    artifact_ids: list[str] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    reason_code: str | None = None
    terminal_phase: str | None = None
    source: str = "task_run_result_and_registry"


class UniversalTaskResultState(AIpinhoModel):
    status: str = "pending"
    summary: str | None = None
    safe_to_display: bool = True
    safe_to_report_success: bool = False
    result_available: bool = False
    block_reason_code: str | None = None
    source: str = "task_run_result"


class UniversalTaskSession(AIpinhoModel):
    task_run_id: str
    public_id: str
    status: UniversalTaskStatus = "CREATED"
    phase: str = "unknown"
    progress: UniversalTaskProgress = Field(default_factory=UniversalTaskProgress)
    eta: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    current_step: str | None = None
    approval_state: UniversalTaskApprovalState = Field(default_factory=UniversalTaskApprovalState)
    validation_state: UniversalTaskValidationState = Field(default_factory=UniversalTaskValidationState)
    artifact_state: UniversalTaskArtifactState = Field(default_factory=UniversalTaskArtifactState)
    result_state: UniversalTaskResultState = Field(default_factory=UniversalTaskResultState)
    events_count: int = 0
    links: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
