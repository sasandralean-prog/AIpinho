from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_get_tools_and_status():
    tools = client.get("/api/v1/tools")
    assert tools.status_code == 200
    body = tools.json()
    assert body["tools"]
    assert any(tool["execute_supported"] is True for tool in body["tools"])
    assert all(
        (not tool["side_effect"] and tool["capability"] == "read_workspace")
        or (tool["requires_approval"] and tool["capability"] in {"shell", "network"})
        for tool in body["tools"]
        if tool["execute_supported"]
    )

    status = client.get("/api/v1/tools/status")
    assert status.status_code == 200
    assert status.json()["real_execution_enabled"] is True
    assert status.json()["write_execution_enabled"] is False


def test_get_tool_by_id():
    response = client.get("/api/v1/tools/filesystem.read_file")
    assert response.status_code == 200
    assert response.json()["tool"]["tool_id"] == "filesystem.read_file"


def test_validate_known_tool():
    response = client.post("/api/v1/tools/validate", json={"tool_id": "filesystem.write_file", "input": {"path": r"C:\Dev\AIpinho\x.txt", "content_preview": "x"}})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "valid"
    assert body["results"][0]["safety"]["status"] == "needs_approval"


def test_validate_unknown_tool_no_500():
    response = client.post("/api/v1/tools/validate", json={"tool_id": "filesystem.teleport", "input": {}})
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["results"][0]["safety"]["blocked_reasons"] == ["unknown_tool"]


def test_preview_endpoint_returns_plan():
    response = client.post("/api/v1/tools/preview", json={"tool_id": "filesystem.read_file", "input": {"workspace": r"C:\Dev\AIpinho", "path": "."}})
    assert response.status_code == 200
    assert response.json()["plan"]["safe_to_execute"] is False


def test_dry_run_endpoint_read_and_write():
    read = client.post("/api/v1/tools/dry-run", json={"tool_id": "filesystem.read_file", "input": {"workspace": r"C:\Dev\AIpinho", "path": "."}})
    assert read.status_code == 200
    assert read.json()["status"] == "simulated"

    write = client.post("/api/v1/tools/dry-run", json={"tool_id": "filesystem.write_file", "input": {"path": r"C:\Dev\AIpinho\x.txt", "content_preview": "x"}})
    assert write.status_code == 200
    assert write.json()["status"] == "needs_approval"
    assert write.json()["result"]["safe_to_execute"] is False


def test_execute_mode_rejected():
    response = client.post("/api/v1/tools/dry-run", json={"tool_id": "shell.run_command", "input": {"command": "echo hi"}, "mode": "execute"})
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert "execute_mode_requested" in response.json()["result"]["tool_results"][0]["would_do"]


def test_web_tool_requires_approval_in_dry_run():
    response = client.post("/api/v1/tools/dry-run", json={"tool_id": "web.request", "input": {"url": "https://example.invalid"}})
    assert response.status_code == 200
    assert response.json()["status"] == "needs_approval"


def test_dry_run_from_draft_and_preview():
    draft_response = client.post("/api/v1/task-drafts", json={"prompt": r"Conserte o bug no projeto C:\Dev\AIpinho"})
    draft = draft_response.json()["draft"]
    from_draft = client.post(f"/api/v1/tools/dry-run/from-draft/{draft['draft_id']}")
    assert from_draft.status_code == 200
    assert from_draft.json()["status"] == "needs_approval"

    preview_response = client.post(f"/api/v1/previews/from-draft/{draft['draft_id']}")
    preview = preview_response.json()["preview"]
    from_preview = client.post(f"/api/v1/tools/dry-run/from-preview/{preview['preview_id']}")
    assert from_preview.status_code == 200
    assert from_preview.json()["status"] == "needs_approval"
