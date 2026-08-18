from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

PhaseProgressionStatus = Literal[
    "pending",
    "allowed_to_start",
    "attempted",
    "executed",
    "accepted_running",
    "completed",
    "completed_with_findings",
    "blocked",
    "failed",
    "cancelled",
    "timeout_blocked",
    "skipped_due_to_prior_block",
    "invalid_post_block_attempt",
]


class FireTestPhaseProgressionState(AIpinhoModel):
    phase: str
    status: PhaseProgressionStatus
    canonical_progression_valid: bool = True
    prior_phase_status: str | None = None
    prior_blocking_phase: str | None = None
    prior_blocking_reason: str | None = None
    allowed_to_start: bool = True
    skip_reason: str | None = None
    task_run_id: str | None = None
    result_ref_id: str | None = None
    safe_to_report_success: bool = False
    reason_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PhaseProgressionGate(AIpinhoModel):
    phase: str
    allowed_to_start: bool
    status: PhaseProgressionStatus
    canonical_progression_valid: bool
    prior_phase_status: str | None = None
    prior_blocking_phase: str | None = None
    prior_blocking_reason: str | None = None
    skip_reason: str | None = None
    reason_code: str | None = None
