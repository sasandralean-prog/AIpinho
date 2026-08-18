from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


MissionStatus = Literal[
    "planned",
    "running",
    "waiting_approval",
    "waiting_user",
    "blocked",
    "completed",
]


class MissionCheckpoint(AIpinhoModel):
    checkpoint_id: str = Field(default_factory=lambda: f"mission_checkpoint_{uuid4().hex}")
    stage: str
    status: MissionStatus
    summary: str
    run_id: str | None = None
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class MissionLifecycle(AIpinhoModel):
    status: MissionStatus = "planned"
    current_stage: str = "planning"
    checkpoints: list[MissionCheckpoint] = Field(default_factory=list)
    updated_at: str = Field(default_factory=utc_now_iso)


class MissionApproval(AIpinhoModel):
    approval_id: str | None = None
    status: Literal["not_required", "pending", "approved", "denied", "blocked"] = "not_required"
    reason: str | None = None
    required_for: list[str] = Field(default_factory=list)


class MissionReview(AIpinhoModel):
    review_id: str = Field(default_factory=lambda: f"mission_review_{uuid4().hex}")
    status: Literal["passed", "warning", "failed"] = "warning"
    summary: str
    findings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class MissionResume(AIpinhoModel):
    mission_id: str
    status: MissionStatus
    current_stage: str
    next_action: str
    checkpoint_count: int = 0


class MissionReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"mission_report_{uuid4().hex}")
    mission_id: str
    status: MissionStatus
    summary: str
    run_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class MissionDashboard(AIpinhoModel):
    mission_id: str
    status: MissionStatus
    current_stage: str
    total_checkpoints: int = 0
    run_count: int = 0
    pending_approval_count: int = 0
    blocked_count: int = 0
    evidence_count: int = 0


class DecisionLogEntry(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"mission_decision_{uuid4().hex}")
    reason: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    chosen_option: str
    rejected_options: list[str] = Field(default_factory=list)
    impact: str = "unknown"
    risk: str = "medium"
    rollback: str = "checkpoint_and_abort"
    worker: str | None = None
    contracts: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    validation: str = "pending"
    timestamp: str = Field(default_factory=utc_now_iso)


class EngineeringMission(AIpinhoModel):
    mission_id: str = Field(default_factory=lambda: f"engineering_mission_{uuid4().hex}")
    objective: str
    session_id: str | None = None
    workspace: str | None = None
    lifecycle: MissionLifecycle = Field(default_factory=MissionLifecycle)
    run_ids: list[str] = Field(default_factory=list)
    approvals: list[MissionApproval] = Field(default_factory=list)
    reviews: list[MissionReview] = Field(default_factory=list)
    decision_log: list[DecisionLogEntry] = Field(default_factory=list)
    reports: list[MissionReport] = Field(default_factory=list)
    dashboard: MissionDashboard | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
