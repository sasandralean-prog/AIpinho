from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.services.approvals.approval_service import ApprovalService
from patch_fixtures import patch_request, patch_workspace

client = TestClient(create_app())


def _plan_with_quality(tmp_path):
    workspace = patch_workspace(tmp_path)
    response = client.post("/api/v1/patch-plans", json=patch_request(workspace).model_dump())
    plan = response.json()["plan"]
    client.post(f"/api/v1/patch-quality/validate-plan/{plan['plan_id']}")
    return workspace, plan


def test_patch_apply_status():
    response = client.get("/api/v1/patch-apply/status")
    assert response.status_code == 200
    data = response.json()["patch_apply"]
    assert data["patch_apply_enabled"] is True
    assert data["shell_enabled"] is False
    assert data["git_enabled"] is False


def test_patch_apply_api_request_approval_create_run_execute(tmp_path):
    workspace, plan = _plan_with_quality(tmp_path)
    before = (workspace / "docs" / "note.md").read_text(encoding="utf-8")
    approval_response = client.post(f"/api/v1/patch-apply/request-approval/{plan['plan_id']}")
    assert approval_response.status_code == 200
    approval_id = approval_response.json()["approval"]["approval_id"]
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before
    ApprovalService().approve(approval_id)
    run_response = client.post(f"/api/v1/patch-apply/runs/from-plan/{plan['plan_id']}", json={"approval_id": approval_id, "operator_confirmed": True})
    assert run_response.status_code == 200
    run = run_response.json()["run"]
    assert run["status"] == "ready_to_execute"
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before
    execute = client.post(f"/api/v1/patch-apply/runs/{run['apply_run_id']}/execute")
    assert execute.status_code == 200
    result = execute.json()["result"]
    assert result["status"] == "completed"
    assert result["post_apply_validation"]["passed"] is True
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == "# New\n"
    assert client.get(f"/api/v1/patch-apply/runs/{run['apply_run_id']}/events").status_code == 200
    assert client.get(f"/api/v1/patch-plans/{plan['plan_id']}/apply-status").status_code == 200


def test_patch_apply_api_blocks_failed_quality(tmp_path):
    workspace = patch_workspace(tmp_path)
    response = client.post("/api/v1/patch-plans", json=patch_request(workspace).model_dump())
    plan_id = response.json()["plan"]["plan_id"]
    (workspace / "docs" / "note.md").write_text("# stale\n", encoding="utf-8")
    quality = client.post(f"/api/v1/patch-quality/validate-plan/{plan_id}")
    assert quality.json()["quality"]["status"] in {"failed", "rejected"}
    approval = client.post(f"/api/v1/patch-apply/request-approval/{plan_id}")
    assert approval.status_code == 409
