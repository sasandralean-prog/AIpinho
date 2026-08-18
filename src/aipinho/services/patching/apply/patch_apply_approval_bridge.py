from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aipinho.schemas.approvals.approval_event import ApprovalEvent
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.patching.apply.patch_apply_hashing import sha256_text
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from aipinho.services.session.session_store import utc_now


class PatchApplyApprovalBridge:
    def __init__(self, plan_store: PatchPlanStore | None = None, approval_store: ApprovalStore | None = None, quality_service: PatchQualityGateService | None = None) -> None:
        self.plan_store = plan_store or PatchPlanStore()
        self.approval_store = approval_store or ApprovalStore()
        self.quality_service = quality_service or PatchQualityGateService(plan_store=self.plan_store)

    def request_approval(self, plan_id: str, *, actor: Actor | None = None, reason: str = "") -> ApprovalRequest:
        plan = self.plan_store.get_plan(plan_id)
        if plan is None:
            raise ValueError("patch_plan_not_found")
        quality = self.quality_service.get_latest_for_plan(plan_id) or self.quality_service.validate_plan(plan_id)
        if quality is None:
            raise ValueError("patch_quality_not_found")
        if quality.status != "passed":
            raise ValueError("patch_quality_not_passed")
        if plan.diff_proposal is None or not plan.diff_proposal.diff.diff_text:
            raise ValueError("patch_diff_not_found")
        diff_hash = sha256_text(plan.diff_proposal.diff.diff_text)
        target_files = [file.relative_path or file.path for file in plan.affected_files]
        original_hashes = {file.relative_path or file.path: file.original_hash or "" for file in plan.affected_files}
        now = datetime.now(timezone.utc)
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=plan.plan_id,
            draft_id=plan.plan_id,
            session_id=None,
            status="pending",
            actions_requested=["patch_apply"],
            approval_scope="patch_apply",
            reason=reason or "PatchApply approval requested after Patch Quality Gate passed. Approval does not apply.",
            risk_level=plan.risk.risk_level,
            policy_snapshot=ApprovalPolicySnapshot(
                policy_status="needs_approval",
                allowed_actions=["patch_apply"],
                denied_actions=["shell", "git_apply", "direct_diff_apply", "payload_patch_apply"],
                approval_required_for=["patch_apply"],
                granted_capabilities=["write_workspace"],
                denied_capabilities=["shell", "git", "memory_write", "rag"],
                workspace_status="allowed",
                risk_level=plan.risk.risk_level,
                trace_hash=diff_hash,
                config_versions={
                    "patch_apply_approval_policy": 1,
                    "plan_id": plan.plan_id,
                    "quality_id": quality.quality_id,
                    "diff_hash": diff_hash,
                    "target_files": target_files,
                    "original_hashes": original_hashes,
                },
            ),
            expires_at=(now + timedelta(minutes=60)).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=actor or Actor(type="system", id="patch_apply_approval_bridge"),
            trace=[{"stage": "patch_apply_approval_bridge", "decision": "pending", "reason": "approval_created_without_apply"}],
            execution_status="not_executed",
        )
        self.approval_store.save(approval)
        self.approval_store.append_event(ApprovalEvent(event_id=f"approval_event_{uuid4().hex}", approval_id=approval.approval_id, event_type="approval_created", created_at=utc_now(), summary="Patch apply approval created; no patch was applied.", data={"plan_id": plan_id, "quality_id": quality.quality_id, "diff_hash": diff_hash}))
        return approval

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_approval_bridge", "approval_executes_apply": False}
