from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.session.session_store import utc_now


ApproverType = Literal["human", "external_adapter", "internal_agent", "service_account", "automation"]
TrustLevel = Literal["L0", "L1", "L2", "L3", "L4"]
ApproverStatus = Literal["active", "disabled", "revoked"]
ApprovalOriginType = Literal["human", "external_adapter", "internal_agent", "service_account", "automation", "system"]
ApprovalAuthority = Literal["AIpinho"]
UniversalApprovalDecision = Literal["approved", "rejected"]


class UniversalApprover(AIpinhoModel):
    approver_id: str
    display_name: str
    approver_type: ApproverType
    trust_level: TrustLevel = "L1"
    capabilities: dict[str, list[str]] = Field(default_factory=dict)
    status: ApproverStatus = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ApprovalOrigin(AIpinhoModel):
    origin_type: ApprovalOriginType
    origin_id: str
    requested_by: str | None = None
    approved_by: str
    approval_authority: ApprovalAuthority = "AIpinho"
    signature: str
    timestamp: str = Field(default_factory=utc_now)


class ApprovalSignature(AIpinhoModel):
    signature_id: str = Field(default_factory=lambda: f"approval_signature_{uuid4().hex}")
    approver_id: str
    session_id: str | None = None
    collaboration_session: str | None = None
    timestamp: str = Field(default_factory=utc_now)
    reason: str = ""
    speaker_truth_reference: str = "approval_decision_recorded_without_execution"
    signature: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class UniversalApprovalTextRequest(AIpinhoModel):
    approver_id: str
    text: str
    session_id: str | None = None
    collaboration_session: str | None = None
    requested_by: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class UniversalApprovalDecisionResult(AIpinhoModel):
    status: str
    approval_id: str
    decision: UniversalApprovalDecision | None = None
    approver_id: str
    reason_code: str | None = None
    human_summary: str
    approval_origin: ApprovalOrigin | None = None
    approval_signature: ApprovalSignature | None = None
    approval: dict[str, Any] | None = None
    resume: dict[str, Any] | None = None
    authority: ApprovalAuthority = "AIpinho"
    external_may_execute: bool = False


class UniversalApproverUpsertRequest(AIpinhoModel):
    approver_id: str
    display_name: str
    approver_type: ApproverType
    trust_level: TrustLevel = "L1"
    capabilities: dict[str, list[str]] = Field(default_factory=dict)
    status: ApproverStatus = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
