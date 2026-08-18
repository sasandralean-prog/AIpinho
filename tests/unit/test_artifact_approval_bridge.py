from pathlib import Path

from artifact_fixtures import artifact_service, artifact_workspace, preview_request
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.artifacts.artifact_approval_bridge import ArtifactApprovalBridge
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore


def test_artifact_approval_bridge_future_write_without_write(tmp_path):
    workspace = artifact_workspace(tmp_path)
    service = artifact_service(tmp_path)
    store = service.store
    preview = service.create_preview(preview_request(workspace))
    bridge = ArtifactApprovalBridge(store=store, approval_store=ApprovalStore(root=tmp_path / "approvals"))
    approval = bridge.request_approval(preview.preview_id)
    assert approval.approval_scope == "future_artifact_write"
    assert approval.execution_status == "not_executed"
    ApprovalService(store=bridge.approval_store).approve(approval.approval_id)
    bridge.record_approval_decision(bridge.approval_store.get(approval.approval_id))
    updated = store.get_preview(preview.preview_id)
    assert updated.status == "approved_for_future_write"
    assert not Path(workspace / "reports" / "analysis.md").exists()


def test_artifact_approval_bridge_rejects_blocked_preview(tmp_path):
    workspace = artifact_workspace(tmp_path)
    service = artifact_service(tmp_path)
    blocked = service.create_preview(preview_request(workspace, target_path="src/app.py"))
    try:
        ArtifactApprovalBridge(store=service.store).request_approval(blocked.preview_id)
    except ValueError as exc:
        assert str(exc) == "artifact_preview_blocked"
    else:
        raise AssertionError("blocked preview should not request approval")
