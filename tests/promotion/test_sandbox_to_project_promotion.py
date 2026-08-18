from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.external_workspace import WorkspaceRegistrationRequest
from aipinho.schemas.promotion import PromotionApplyRequest, PromotionApprovalRequest, PromotionPlanRequest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.promotion.promotion_pipeline_service import PromotionPipelineService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService
from aipinho.services.workspaces.external_workspace_service import ExternalWorkspaceService


def _env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "sandbox_data"))
    monkeypatch.setenv("AIPINHO_EXTERNAL_WORKSPACE_DATA_ROOT", str(tmp_path / "external_data"))
    monkeypatch.setenv("AIPINHO_PROMOTION_DATA_ROOT", str(tmp_path / "promotion_data"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))


def _source(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "README.md").write_text("# New Project\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('new')\n", encoding="utf-8")
    return root


def _target(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "README.md").write_text("# Old Project\n", encoding="utf-8")
    return root


def test_promotion_requires_target_mutable(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _source(tmp_path / "source")
    target = _target(tmp_path / "target")
    workspaces = ExternalWorkspaceService()
    readonly = workspaces.register(WorkspaceRegistrationRequest(path=str(target), role="source_readonly"))

    plan = PromotionPipelineService().create_plan(PromotionPlanRequest(source_path=str(source), target_workspace_id=readonly.workspace_id))
    assert plan.status == "blocked"
    assert "target_mutable_required" in plan.errors


def test_promotion_preview_approval_apply_and_validation(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _source(tmp_path / "sandbox_source")
    target = _target(tmp_path / "target_mutable")
    service = ExternalWorkspaceService()
    target_registration = service.register(WorkspaceRegistrationRequest(path=str(target), role="target_mutable"))
    promotion = PromotionPipelineService()

    plan = promotion.create_plan(PromotionPlanRequest(source_path=str(source), target_workspace_id=target_registration.workspace_id))
    assert plan.status == "preview"
    assert plan.files_to_create == 1
    assert plan.files_to_modify == 1
    assert plan.requires_approval is True

    preview = promotion.create_preview(plan.promotion_plan_id)
    blocked = promotion.apply(PromotionApplyRequest(preview_id=preview.preview_id))
    assert blocked.status == "blocked"
    assert "promotion_approval_required" in blocked.errors

    approval = promotion.approve(PromotionApprovalRequest(preview_id=preview.preview_id, approved_by="tester"))
    result = promotion.apply(PromotionApplyRequest(preview_id=preview.preview_id, approval_id=approval.approval_id))
    assert result.status == "completed"
    assert "src/main.py" in result.files_created
    assert "README.md" in result.files_modified
    assert result.validation and result.validation.status == "passed"
    assert result.rollback_plan and result.rollback_plan.snapshot_root
    assert result.artifact_id
    assert result.download_endpoint and "token" not in result.download_endpoint.lower()
    assert (target / "README.md").read_text(encoding="utf-8") == "# New Project\n"
    assert (source / "README.md").read_text(encoding="utf-8") == "# New Project\n"

    artifact, content = AgentToolGatewayService().read_artifact_bytes(result.artifact_id)
    assert artifact.requires_token is True
    assert b"Promotion Report" in content


def test_promotion_blocks_binary_and_path_escape_is_not_applied(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _source(tmp_path / "binary_source")
    (source / "asset.bin").write_bytes(b"\x00\x01binary")
    target = _target(tmp_path / "binary_target")
    target_registration = ExternalWorkspaceService().register(WorkspaceRegistrationRequest(path=str(target), role="target_mutable"))
    promotion = PromotionPipelineService()

    plan = promotion.create_plan(PromotionPlanRequest(source_path=str(source), target_workspace_id=target_registration.workspace_id))
    assert any(item.operation == "blocked" and item.relative_path == "asset.bin" for item in plan.diff_items)

    preview = promotion.create_preview(plan.promotion_plan_id)
    approval = promotion.approve(PromotionApprovalRequest(preview_id=preview.preview_id))
    result = promotion.apply(PromotionApplyRequest(preview_id=preview.preview_id, approval_id=approval.approval_id))
    assert "asset.bin" in result.files_blocked
    assert not (target / "asset.bin").exists()


def test_promotion_api_flow(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _source(tmp_path / "api_source")
    target = _target(tmp_path / "api_target")
    target_registration = ExternalWorkspaceService().register(WorkspaceRegistrationRequest(path=str(target), role="target_mutable"))
    client = TestClient(app)

    plan_response = client.post("/api/v1/promotion/plans", json={"source_path": str(source), "target_workspace_id": target_registration.workspace_id})
    assert plan_response.status_code == 200
    plan_id = plan_response.json()["promotion_plan_id"]
    preview_response = client.post(f"/api/v1/promotion/plans/{plan_id}/preview")
    assert preview_response.status_code == 200
    preview_id = preview_response.json()["preview_id"]
    blocked = client.post("/api/v1/promotion/apply", json={"preview_id": preview_id})
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"
    approval = client.post("/api/v1/promotion/approvals", json={"preview_id": preview_id, "approved_by": "tester"})
    assert approval.status_code == 200
    applied = client.post("/api/v1/promotion/apply", json={"preview_id": preview_id, "approval_id": approval.json()["approval_id"]})
    assert applied.status_code == 200
    assert applied.json()["status"] == "completed"
