from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


PromotionStatus = Literal["preview", "approval_required", "approved", "applying", "completed", "blocked", "failed", "validation_failed"]
PromotionOperationType = Literal["create", "modify", "delete", "unchanged", "blocked"]


class PromotionPlanRequest(AIpinhoModel):
    source_path: str | None = None
    sandbox_workspace_id: str | None = None
    target_workspace_id: str
    include_globs: list[str] = Field(default_factory=lambda: ["**/*"])
    exclude_globs: list[str] = Field(default_factory=list)
    require_approval: bool | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class PromotionDiffItem(AIpinhoModel):
    relative_path: str
    operation: PromotionOperationType
    source_hash: str | None = None
    target_hash: str | None = None
    size_bytes: int = 0
    risk_level: str = "low"
    requires_approval: bool = False
    reason_code: str = "diff_detected"
    warnings: list[str] = Field(default_factory=list)


class RollbackPlan(AIpinhoModel):
    rollback_plan_id: str = Field(default_factory=lambda: f"rollback_plan_{uuid4().hex}")
    snapshot_root: str | None = None
    affected_files: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class PromotionPlan(AIpinhoModel):
    promotion_plan_id: str = Field(default_factory=lambda: f"promotion_plan_{uuid4().hex}")
    source_path: str
    target_workspace_id: str
    target_path: str
    status: PromotionStatus = "preview"
    diff_items: list[PromotionDiffItem] = Field(default_factory=list)
    files_to_create: int = 0
    files_to_modify: int = 0
    files_blocked: int = 0
    risk_level: str = "low"
    requires_approval: bool = False
    validation_plan: list[str] = Field(default_factory=list)
    rollback_plan: RollbackPlan | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class PromotionPreview(AIpinhoModel):
    preview_id: str = Field(default_factory=lambda: f"promotion_preview_{uuid4().hex}")
    promotion_plan_id: str
    status: PromotionStatus = "preview"
    target_workspace_id: str
    diff_items: list[PromotionDiffItem] = Field(default_factory=list)
    risk_level: str = "low"
    requires_approval: bool = False
    expected_side_effects: list[str] = Field(default_factory=list)
    validation_plan: list[str] = Field(default_factory=list)
    rollback_plan: RollbackPlan | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class PromotionApprovalRequest(AIpinhoModel):
    preview_id: str
    approved_by: str = "user"
    reason: str | None = None


class PromotionApprovalResult(AIpinhoModel):
    approval_id: str = Field(default_factory=lambda: f"promotion_approval_{uuid4().hex}")
    preview_id: str
    status: str = "approved"
    approved_by: str = "user"
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class PromotionApplyRequest(AIpinhoModel):
    preview_id: str
    approval_id: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class PromotionValidationResult(AIpinhoModel):
    validation_id: str = Field(default_factory=lambda: f"promotion_validation_{uuid4().hex}")
    status: str
    checks: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class PromotionApplyResult(AIpinhoModel):
    apply_id: str = Field(default_factory=lambda: f"promotion_apply_{uuid4().hex}")
    preview_id: str
    status: PromotionStatus
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    files_blocked: list[str] = Field(default_factory=list)
    rollback_plan: RollbackPlan | None = None
    validation: PromotionValidationResult | None = None
    artifact_id: str | None = None
    download_endpoint: str | None = None
    requires_token: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class PromotionReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"promotion_report_{uuid4().hex}")
    status: str
    plan_id: str | None = None
    preview_id: str | None = None
    apply_id: str | None = None
    validation_id: str | None = None
    artifact_id: str | None = None
    summary: str
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
