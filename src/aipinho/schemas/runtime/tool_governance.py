from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


ToolGovernanceStage = Literal[
    "intent",
    "planner",
    "contract",
    "capability",
    "policy",
    "approval",
    "tool_router",
    "execution",
    "validation",
    "artifacts",
    "report",
]
ToolGovernanceCheckpointStatus = Literal[
    "present",
    "not_required",
    "missing",
    "blocked",
    "pending",
]
ToolGovernanceTrailStatus = Literal["ready", "incomplete", "blocked"]
ToolGovernanceAuditStatus = Literal["passed", "failed"]


class ToolGovernanceCheckpoint(AIpinhoModel):
    checkpoint_id: str = Field(default_factory=lambda: f"tool_gov_checkpoint_{uuid4().hex}")
    stage: ToolGovernanceStage
    status: ToolGovernanceCheckpointStatus
    summary: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    required: bool = True
    created_at: str = Field(default_factory=utc_now_iso)


class ToolGovernanceTrail(AIpinhoModel):
    trail_id: str = Field(default_factory=lambda: f"tool_gov_trail_{uuid4().hex}")
    run_id: str
    status: ToolGovernanceTrailStatus
    action: str | None = None
    contract_type: str | None = None
    operation_type: str | None = None
    runtime_profile: str | None = None
    checkpoints: list[ToolGovernanceCheckpoint] = Field(default_factory=list)
    missing_required_stages: list[ToolGovernanceStage] = Field(default_factory=list)
    blocked_stages: list[ToolGovernanceStage] = Field(default_factory=list)
    traceable: bool = False
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class ToolGovernanceAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"tool_gov_audit_{uuid4().hex}")
    trail_id: str
    run_id: str
    status: ToolGovernanceAuditStatus
    reason: str
    missing_required_stages: list[ToolGovernanceStage] = Field(default_factory=list)
    blocked_stages: list[ToolGovernanceStage] = Field(default_factory=list)
    traceable: bool = False
    created_at: str = Field(default_factory=utc_now_iso)
