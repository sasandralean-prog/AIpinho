from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


SelfHealingCandidateStatus = Literal["proposed", "triaged", "approved", "rejected", "applied", "blocked", "superseded"]
SelfHealingRisk = Literal["low", "medium", "high", "critical"]


class SelfHealingAction(AIpinhoModel):
    action_id: str = Field(default_factory=lambda: f"self_healing_action_{uuid4().hex}")
    action_type: str
    label: str
    side_effect: str = "derived_state_only"
    reversible: bool = True
    requires_approval: bool = False
    validation_required: bool = True
    endpoint_ref: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SelfHealingCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"self_healing_candidate_{uuid4().hex}")
    detector_id: str
    issue_type: str
    status: SelfHealingCandidateStatus = "proposed"
    risk_level: SelfHealingRisk = "low"
    entity_type: str
    entity_id: str
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    recommended_actions: list[SelfHealingAction] = Field(default_factory=list)
    policy_decision: str = "review_required"
    approval_required: bool = False
    block_reason_code: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SelfHealingRun(AIpinhoModel):
    self_healing_run_id: str = Field(default_factory=lambda: f"self_healing_run_{uuid4().hex}")
    candidate_id: str
    action_id: str | None = None
    action_type: str
    status: str = "created"
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    approval_id: str | None = None
    validation_status: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    summary: str
    warnings: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SelfHealingScanRequest(AIpinhoModel):
    detector_ids: list[str] = Field(default_factory=list)
    persist: bool = True


class SelfHealingTriageRequest(AIpinhoModel):
    decision: Literal["approve", "reject", "defer"]
    reason: str | None = None


class SelfHealingApplyRequest(AIpinhoModel):
    action_id: str | None = None
    approval_id: str | None = None
    dry_run: bool = False


class SelfHealingRejectRequest(AIpinhoModel):
    reason: str | None = None


class SelfHealingStatus(AIpinhoModel):
    status: str
    detectors_loaded: int
    candidates_total: int
    candidates_open: int
    runs_total: int
    auto_fix_enabled: bool
    raw_default_visible: bool = False


class SelfHealingExportReportRequest(AIpinhoModel):
    include_candidates: bool = True
    include_runs: bool = True
    include_status: bool = True
