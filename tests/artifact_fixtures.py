from __future__ import annotations

import os
import shutil
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_preview import ArtifactPreviewRequest
from aipinho.schemas.artifacts.artifact_source import ArtifactSource
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.artifacts.artifact_approval_bridge import ArtifactApprovalBridge
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore
from aipinho.services.artifacts.artifact_target_policy_service import ArtifactTargetPolicyService
from aipinho.services.artifacts.artifact_writer_preview_service import ArtifactWriterPreviewService
from aipinho.utils.yaml_loader import load_yaml_file


def _artifact_test_root(tmp_path: Path) -> Path:
    return tmp_path / "artifact_mutable_root"


def _artifact_test_policy(tmp_path: Path) -> ArtifactTargetPolicyService:
    policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_target_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
    targets = dict(policy.get("targets", {}) if isinstance(policy.get("targets"), dict) else {})
    targets["allowed_workspace_roots"] = [str(_artifact_test_root(tmp_path))]
    policy = {**policy, "targets": targets}
    return ArtifactTargetPolicyService(policy=policy)


def artifact_workspace(tmp_path: Path) -> Path:
    default_root = _artifact_test_root(tmp_path)
    os.environ["AIPINHO_TEST_PROFILE"] = "1"
    os.environ["AIPINHO_TEST_MUTABLE_ROOT"] = str(default_root)
    root = Path(os.environ["AIPINHO_TEST_MUTABLE_ROOT"])
    workspace = root / tmp_path.name / "artifact_workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    (workspace / "reports").mkdir()
    (workspace / "exports").mkdir()
    return workspace


def preview_request(workspace: Path, target_path: str = "reports/analysis.md", content: str = "# Report\n\nOk.", fmt: str = "markdown") -> ArtifactPreviewRequest:
    return ArtifactPreviewRequest(
        workspace=str(workspace),
        target_path=target_path,
        source=ArtifactSource(source_type="user_provided_content", format=fmt, content=content),
        artifact_type="report",
        title="Artifact preview test",
    )


def artifact_service(tmp_path: Path) -> ArtifactWriterPreviewService:
    return ArtifactWriterPreviewService(store=ArtifactPreviewStore(root=tmp_path / "artifact_store"), target_policy=_artifact_test_policy(tmp_path))


def approved_artifact_preview(tmp_path: Path, target_path: str = "reports/analysis.md", content: str = "# Report\n\nOk.", allow_overwrite: bool = False):
    workspace = artifact_workspace(tmp_path)
    if allow_overwrite:
        target = workspace / target_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("old", encoding="utf-8")
    preview_service = artifact_service(tmp_path)
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    bridge = ArtifactApprovalBridge(store=preview_service.store, approval_store=approval_store)
    preview = preview_service.create_preview(preview_request(workspace, target_path=target_path, content=content))
    approval = bridge.request_approval(preview.preview_id)
    _, approval = ApprovalService(store=approval_store).approve(approval.approval_id)
    bridge.record_approval_decision(approval)
    return workspace, preview_service.store, approval_store, preview_service.store.get_preview(preview.preview_id), approval
