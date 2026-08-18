from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aipinho.schemas.approvals.approval_event import ApprovalEvent
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore
from aipinho.services.artifacts.artifact_trace_service import ArtifactTraceService
from aipinho.services.session.session_store import utc_now


class ArtifactApprovalBridge:
    def __init__(self, store: ArtifactPreviewStore | None = None, approval_store: ApprovalStore | None = None) -> None:
        self.store = store or ArtifactPreviewStore()
        self.approval_store = approval_store or ApprovalStore()
        self.trace = ArtifactTraceService()

    def request_approval(self, preview_id: str, *, actor: Actor | None = None, reason: str = "") -> ApprovalRequest:
        preview = self.store.get_preview(preview_id)
        if preview is None:
            raise ValueError("artifact_preview_not_found")
        if preview.status == "blocked" or preview.risk.blocked:
            raise ValueError("artifact_preview_blocked")
        if preview.risk.risk_level == "critical":
            raise ValueError("artifact_preview_critical_risk")
        if not preview.validation.valid:
            raise ValueError("artifact_preview_validation_failed")
        now = datetime.now(timezone.utc)
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=preview.preview_id,
            draft_id=preview.draft_id or preview.preview_id,
            session_id=None,
            status="pending",
            actions_requested=["artifact_write_future"],
            approval_scope="future_artifact_write",
            reason=reason or "Artifact preview requires approval for future write. Sprint 18 does not execute writes.",
            risk_level=preview.risk.risk_level,
            policy_snapshot=ApprovalPolicySnapshot(
                policy_status="needs_approval",
                allowed_actions=[],
                denied_actions=["artifact_write_execute", "write_files", "overwrite_file", "create_directory", "apply_patch"],
                approval_required_for=["artifact_write_future"],
                granted_capabilities=[],
                denied_capabilities=["write_workspace"],
                workspace_status="allowed" if preview.validation.target.workspace_allowed else "blocked",
                risk_level=preview.risk.risk_level,
                trace_hash=preview.content_hash,
                config_versions={"artifact_approval_policy": 1},
            ),
            expires_at=(now + timedelta(minutes=60)).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=actor or Actor(type="system", id="artifact_approval_bridge"),
            trace=[self.trace.item("artifact_approval_bridge", "pending", "future_artifact_write_approval_created_without_write", source="services/artifacts/artifact_approval_bridge.py").model_dump()],
            execution_status="not_executed",
        )
        self.approval_store.save(approval)
        self._append_event(approval.approval_id, "approval_created", "Artifact approval created for future write only; no file was written.")
        self.store.update_preview_status(preview.preview_id, "approval_pending", approval_id=approval.approval_id, approval_status="pending")
        return approval

    def record_approval_decision(self, approval: ApprovalRequest) -> None:
        if approval.approval_scope != "future_artifact_write":
            return
        preview = self.store.get_preview(approval.preview_id)
        if preview is None:
            return
        status_map = {
            "approved": "approved_for_future_write",
            "rejected": "rejected",
            "cancelled": "cancelled",
            "expired": "expired",
            "invalidated_by_policy_change": "invalidated",
            "pending": "approval_pending",
        }
        next_status = status_map.get(approval.status, "invalidated")
        self.store.update_preview_status(preview.preview_id, next_status, approval_id=approval.approval_id, approval_status=approval.status)

    def _append_event(self, approval_id: str, event_type: str, summary: str) -> None:
        event = ApprovalEvent(event_id=f"approval_event_{uuid4().hex}", approval_id=approval_id, event_type=event_type, created_at=utc_now(), summary=summary, data={"artifact_preview": True, "write_executed": False})
        self.approval_store.append_event(event)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_approval_bridge", "approval_executes_write": False}
