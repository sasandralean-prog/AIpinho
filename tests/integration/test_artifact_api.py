from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from artifact_fixtures import artifact_workspace

client = TestClient(create_app())


def payload(workspace: Path, target_path: str = "reports/api.md", content: str = "# API\n\nOk.", fmt: str = "markdown"):
    return {
        "workspace": str(workspace),
        "target_path": target_path,
        "source": {"source_type": "user_provided_content", "format": fmt, "content": content},
        "artifact_type": "report",
        "title": "API artifact preview",
    }


def test_artifact_status_endpoint():
    response = client.get("/api/v1/artifacts/status")
    assert response.status_code == 200
    data = response.json()["artifact_writer"]
    assert data["mode"] == "preview_only"
    assert data["write_enabled"] is False


def test_artifact_drafts_and_previews_api(tmp_path):
    workspace = artifact_workspace(tmp_path)
    created = client.post("/api/v1/artifacts/drafts", json=payload(workspace))
    assert created.status_code == 200
    draft_id = created.json()["draft"]["draft_id"]
    assert client.get(f"/api/v1/artifacts/drafts/{draft_id}").status_code == 200
    preview = client.post("/api/v1/artifacts/previews", json={**payload(workspace), "draft_id": draft_id})
    assert preview.status_code == 200
    preview_id = preview.json()["preview"]["preview_id"]
    assert client.get(f"/api/v1/artifacts/previews/{preview_id}").status_code == 200
    assert client.get(f"/api/v1/artifacts/previews/{preview_id}/diff").status_code == 200
    assert client.get(f"/api/v1/artifacts/previews/{preview_id}/trace").status_code == 200
    assert not (workspace / "reports" / "api.md").exists()


def test_artifact_api_blocks_forbidden_and_source_code(tmp_path):
    workspace = artifact_workspace(tmp_path)
    outside_allowed_root = tmp_path / "outside_allowed_root"
    outside_allowed_root.mkdir()
    forbidden = client.post("/api/v1/artifacts/previews", json=payload(outside_allowed_root, "reports/a.md"))
    source_code = client.post("/api/v1/artifacts/previews", json=payload(workspace, "src/app.py"))
    assert forbidden.status_code == 200
    assert forbidden.json()["preview"]["status"] == "blocked"
    assert "workspace_root_not_allowed" in forbidden.json()["preview"]["blocked_reasons"]
    assert source_code.status_code == 200
    assert source_code.json()["preview"]["status"] == "blocked"


def test_artifact_api_approval_request_does_not_write(tmp_path):
    workspace = artifact_workspace(tmp_path)
    created = client.post("/api/v1/artifacts/previews", json=payload(workspace))
    preview_id = created.json()["preview"]["preview_id"]
    approval = client.post(f"/api/v1/artifacts/previews/{preview_id}/request-approval")
    assert approval.status_code == 200
    assert approval.json()["approval"]["approval_scope"] == "future_artifact_write"
    assert not (workspace / "reports" / "api.md").exists()


def test_artifact_api_refresh_validation(tmp_path):
    workspace = artifact_workspace(tmp_path)
    created = client.post("/api/v1/artifacts/previews", json=payload(workspace))
    preview_id = created.json()["preview"]["preview_id"]
    (workspace / "reports").mkdir(exist_ok=True)
    (workspace / "reports" / "api.md").write_text("old", encoding="utf-8")
    refreshed = client.post(f"/api/v1/artifacts/previews/{preview_id}/refresh-validation")
    assert refreshed.status_code == 200
    assert refreshed.json()["preview"]["would_overwrite"] is True


def test_task_run_summary_zip_route_requires_validated_result():
    response = client.post(
        "/api/v1/artifacts/from-task-run/task_run_00000000000000000000000000000000/summary-zip",
        json={"summary_filename": "summary.txt", "zip_filename": "summary.zip"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "task_run_result_not_found"
