from datetime import datetime, timedelta, timezone

from artifact_fixtures import approved_artifact_preview, artifact_service, artifact_workspace, preview_request
from aipinho.schemas.artifacts.artifact_write_request import ArtifactWriteRequest
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.artifacts.artifact_approval_bridge import ArtifactApprovalBridge
from aipinho.services.artifacts.artifact_write_guard_service import ArtifactWriteGuardService


def test_guard_allows_approved_preview_real(tmp_path):
    _, preview_store, approval_store, preview, approval = approved_artifact_preview(tmp_path)
    request = ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True)
    guard = ArtifactWriteGuardService(preview_store, approval_store).validate(request)
    assert guard.allowed is True
    assert guard.content_hash == preview.content_hash


def test_guard_blocks_missing_rejected_expired_and_not_approved(tmp_path):
    workspace = artifact_workspace(tmp_path)
    preview_service = artifact_service(tmp_path)
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    preview = preview_service.create_preview(preview_request(workspace))
    missing = ArtifactWriteGuardService(preview_service.store, approval_store).validate(ArtifactWriteRequest(preview_id=preview.preview_id, approval_id="missing", operator_confirmed=True))
    assert "approval_missing" in missing.blocked_reasons
    approval = ArtifactApprovalBridge(store=preview_service.store, approval_store=approval_store).request_approval(preview.preview_id)
    from aipinho.services.approvals.approval_service import ApprovalService
    rejected = ApprovalService(store=approval_store).reject(approval.approval_id)[1]
    ArtifactApprovalBridge(store=preview_service.store, approval_store=approval_store).record_approval_decision(rejected)
    guard = ArtifactWriteGuardService(preview_service.store, approval_store).validate(ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True))
    assert "approval_rejected" in guard.blocked_reasons
    rejected.status = "approved"
    rejected.expires_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    approval_store.save(rejected)
    preview_service.store.update_preview_status(preview.preview_id, "approved_for_future_write", approval_id=approval.approval_id, approval_status="approved")
    expired = ArtifactWriteGuardService(preview_service.store, approval_store).validate(ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True))
    assert "approval_expired" in expired.blocked_reasons


def test_guard_blocks_forbidden_source_code_secret_and_overwrite_rules(tmp_path):
    workspace = artifact_workspace(tmp_path)
    preview_service = artifact_service(tmp_path)
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    blocked = preview_service.create_preview(preview_request(workspace, target_path="src/app.py"))
    request = ArtifactWriteRequest(preview_id=blocked.preview_id, approval_id="missing", operator_confirmed=True)
    guard = ArtifactWriteGuardService(preview_service.store, approval_store).validate(request)
    assert "source_code_target" in guard.blocked_reasons
    _, preview_store, approval_store, preview, approval = approved_artifact_preview(tmp_path / "ow", allow_overwrite=True)
    guard = ArtifactWriteGuardService(preview_store, approval_store).validate(ArtifactWriteRequest(preview_id=preview.preview_id, approval_id=approval.approval_id, operator_confirmed=True))
    assert "overwrite_requires_explicit_approval" in guard.blocked_reasons
