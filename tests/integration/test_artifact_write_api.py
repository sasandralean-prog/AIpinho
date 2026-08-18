from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from artifact_fixtures import artifact_workspace

client = TestClient(create_app())


def payload(workspace: Path, target_path: str = "reports/api-write.md", content: str = "# API Write\n\nOk."):
    return {
        "workspace": str(workspace),
        "target_path": target_path,
        "source": {"source_type": "user_provided_content", "format": "markdown", "content": content},
        "artifact_type": "report",
        "title": "API artifact write",
    }


def approve_preview(preview_id: str):
    approval = client.post(f"/api/v1/artifacts/previews/{preview_id}/request-approval")
    assert approval.status_code == 200
    approval_id = approval.json()["approval"]["approval_id"]
    decided = client.post(f"/api/v1/approvals/{approval_id}/approve")
    assert decided.status_code == 200
    return approval_id


def test_artifact_write_status_endpoint():
    response = client.get("/api/v1/artifacts/write/status")
    assert response.status_code == 200
    data = response.json()["artifact_write"]
    assert data["enabled"] is True
    assert data["mode"] == "approved_non_code_writes"
    assert data["direct_payload_write_enabled"] is False
    assert data["source_code_write_enabled"] is False


def test_artifact_write_api_approved_new_file_flow(tmp_path):
    workspace = artifact_workspace(tmp_path)
    preview = client.post("/api/v1/artifacts/previews", json=payload(workspace))
    preview_id = preview.json()["preview"]["preview_id"]
    approval_id = approve_preview(preview_id)
    run_response = client.post(f"/api/v1/artifacts/write/from-preview/{preview_id}", json={"preview_id": preview_id, "approval_id": approval_id, "operator_confirmed": True})
    assert run_response.status_code == 200
    run = run_response.json()["write_run"]
    assert run["status"] == "ready_to_execute"
    assert not (workspace / "reports" / "api-write.md").exists()
    result = client.post(f"/api/v1/artifacts/write/{run['write_run_id']}/execute")
    assert result.status_code == 200
    assert result.json()["result"]["status"] == "completed"
    assert (workspace / "reports" / "api-write.md").exists()
    assert client.get(f"/api/v1/artifacts/write/runs/{run['write_run_id']}").status_code == 200
    assert client.get(f"/api/v1/artifacts/write/runs/{run['write_run_id']}/events").status_code == 200
    assert client.get(f"/api/v1/artifacts/write/runs/{run['write_run_id']}/result").status_code == 200


def test_artifact_write_api_blocks_missing_approval_and_source_code(tmp_path):
    workspace = artifact_workspace(tmp_path)
    preview = client.post("/api/v1/artifacts/previews", json=payload(workspace))
    preview_id = preview.json()["preview"]["preview_id"]
    run_response = client.post(f"/api/v1/artifacts/write/from-preview/{preview_id}", json={"preview_id": preview_id, "approval_id": "missing", "operator_confirmed": True})
    assert run_response.status_code == 200
    assert run_response.json()["write_run"]["status"] == "blocked"
    source = client.post("/api/v1/artifacts/previews", json=payload(workspace, "src/app.py"))
    source_id = source.json()["preview"]["preview_id"]
    blocked = client.post(f"/api/v1/artifacts/write/from-preview/{source_id}", json={"preview_id": source_id, "approval_id": "missing", "operator_confirmed": True})
    assert blocked.json()["write_run"]["status"] == "blocked"
