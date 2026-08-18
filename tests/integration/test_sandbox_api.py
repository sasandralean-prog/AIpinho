from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app


def test_sandbox_api_happy_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "data"))
    client = TestClient(app)

    status = client.get("/api/v1/sandbox/status")
    assert status.status_code == 200
    workspace_id = "sandbox_ws_default"

    task = client.post("/api/v1/sandbox/tasks", json={"sandbox_workspace_id": workspace_id, "title": "API sandbox task"})
    assert task.status_code == 200
    task_id = task.json()["sandbox_task_id"]

    write = client.post("/api/v1/sandbox/files/write", json={"sandbox_workspace_id": workspace_id, "sandbox_task_id": task_id, "relative_path": "notes/result.txt", "content": "ok", "overwrite": True})
    assert write.status_code == 200
    assert write.json()["status"] == "succeeded"

    blocked = client.post("/api/v1/sandbox/files/write", json={"sandbox_workspace_id": workspace_id, "relative_path": "../escape.txt", "content": "no"})
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["reason_code"] == "sandbox_path_traversal_blocked"

    export = client.post("/api/v1/sandbox/artifacts/export", json={"sandbox_workspace_id": workspace_id, "sandbox_task_id": task_id, "filename": "result.zip", "include_paths": ["notes"]})
    assert export.status_code == 200
    assert export.json()["status"] == "ready"
    assert export.json()["artifact_id"]
    assert export.json()["requires_token"] is True

    view = client.get("/api/v1/mobile/view-model/sandbox")
    assert view.status_code == 200
    assert view.json()["raw_default_visible"] is False
