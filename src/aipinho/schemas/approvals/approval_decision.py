from __future__ import annotations

from pydantic import Field

from aipinho.schemas.approvals.universal_approver import ApprovalOrigin, ApprovalSignature
from aipinho.schemas.approvals.approval_state import ApprovalDecisionValue
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel


class ApprovalDecision(AIpinhoModel):
    approval_id: str
    decision: ApprovalDecisionValue
    actor: Actor = Field(default_factory=Actor)
    reason: str = ""
    scope: str = "single_action"
    decided_at: str
    policy_snapshot_hash: str
    approval_origin: ApprovalOrigin | None = None
    approval_signature: ApprovalSignature | None = None
    approval_authority: str = "AIpinho"
    trace: list[dict[str, object]] = Field(default_factory=list)
    execution_status: str = "not_executed"
