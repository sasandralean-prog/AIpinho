from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


ContinuousRuntimeStage = Literal[
    "objective",
    "plan",
    "execution",
    "observation",
    "correction",
    "continuation",
    "conclusion",
]
ContinuousRuntimeStatus = Literal[
    "continue",
    "completed",
    "needs_approval",
    "needs_user",
    "blocked",
]


class ContinuousRuntimeCheckpoint(AIpinhoModel):
    checkpoint_id: str = Field(default_factory=lambda: f"continuous_checkpoint_{uuid4().hex}")
    stage: ContinuousRuntimeStage
    status: ContinuousRuntimeStatus
    summary: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class ContinuousRuntimeCycle(AIpinhoModel):
    cycle_id: str = Field(default_factory=lambda: f"continuous_cycle_{uuid4().hex}")
    run_id: str
    objective: str
    status: ContinuousRuntimeStatus = "continue"
    current_stage: ContinuousRuntimeStage = "objective"
    checkpoints: list[ContinuousRuntimeCheckpoint] = Field(default_factory=list)
    next_action: str = "observe"
    reason_code: str | None = None
    approval_id: str | None = None
    needs_user_reason: str | None = None
    blocked_reason: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ContinuousRuntimeResume(AIpinhoModel):
    cycle_id: str
    run_id: str
    status: ContinuousRuntimeStatus
    next_action: str
    current_stage: ContinuousRuntimeStage
    reason_code: str | None = None
    checkpoint_count: int = 0
