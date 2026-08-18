from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

BlockedStage = Literal[
    "intent_routing",
    "workspace_resolution",
    "source_read_policy",
    "artifact_output_policy",
    "approval_required",
    "approval_denied",
    "execution_failed",
    "validation_failed",
    "artifact_packaging_failed",
    "report_generation_failed",
    "unknown",
]


class TaskBlockCause(AIpinhoModel):
    block_id: str
    task_id: str
    operation_id: str | None = None
    operation_type: str | None = None
    blocked_stage: BlockedStage = "unknown"
    block_reason_code: str
    human_reason: str
    technical_reason_sanitized: str
    policy_name: str | None = None
    policy_decision_id: str | None = None
    capability_requested: str | None = None
    workspace_id: str | None = None
    workspace_role: str | None = None
    source_read_status: str | None = None
    artifact_output_status: str | None = None
    approval_status: str | None = None
    validation_status: str | None = None
    validation_id: str | None = None
    failure_summary: str | None = None
    failed_checks: list[str] = Field(default_factory=list)
    safe_alternatives: list[str] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    trace_id: str | None = None
    event_id: str | None = None
