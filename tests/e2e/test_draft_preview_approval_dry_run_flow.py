from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_readonly_draft_preview_dry_run_flow():
    draft = client.post("/api/v1/task-drafts", json={"prompt": r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada"}).json()["draft"]
    preview = client.post(f"/api/v1/previews/from-draft/{draft['draft_id']}").json()["preview"]
    result = client.post(f"/api/v1/tools/dry-run/from-preview/{preview['preview_id']}")
    assert result.status_code == 200
    assert result.json()["status"] == "simulated"
    assert result.json()["result"]["safe_to_execute"] is False


def test_artifact_preview_approval_dry_run_no_execution():
    target = Path(r"C:\Dev\AIpinho\reports\sprints\e2e_should_not_be_written.txt")
    draft = client.post("/api/v1/task-drafts", json={"prompt": r"Salve um relatorio em reports/final.md no projeto C:\\Dev\\AIpinho"}).json()["draft"]
    preview = client.post(f"/api/v1/previews/from-draft/{draft['draft_id']}").json()["preview"]
    approval = client.post("/api/v1/approvals", json={"preview_id": preview["preview_id"], "reason": "dry-run e2e"}).json()["approval"]
    approved = client.post(f"/api/v1/approvals/{approval['approval_id']}/approve", json={"reason": "future only"})
    assert approved.status_code == 200

    result = client.post("/api/v1/tools/dry-run", json={"tool_id": "filesystem.write_file", "approval_id": approval["approval_id"], "input": {"path": str(target), "content_preview": "x"}})
    assert result.status_code == 200
    assert result.json()["status"] == "needs_approval"
    assert result.json()["result"]["safe_to_execute"] is False
    assert target.exists() is False


def test_patch_preview_approval_dry_run_no_patch():
    draft = client.post("/api/v1/task-drafts", json={"prompt": r"Conserte o bug no projeto C:\Dev\AIpinho"}).json()["draft"]
    preview = client.post(f"/api/v1/previews/from-draft/{draft['draft_id']}").json()["preview"]
    approval = client.post("/api/v1/approvals", json={"preview_id": preview["preview_id"], "reason": "dry-run patch"}).json()["approval"]
    client.post(f"/api/v1/approvals/{approval['approval_id']}/approve", json={"reason": "future only"})
    result = client.post(f"/api/v1/tools/dry-run/from-preview/{preview['preview_id']}")
    assert result.status_code == 200
    assert result.json()["status"] == "needs_approval"
    assert any(item["tool_id"] == "patch.apply" for item in result.json()["result"]["tool_results"])


def test_forbidden_root_dry_run_blocked():
    draft = client.post("/api/v1/task-drafts", json={"prompt": r"Corrija C:\PinhoabacaxiAI"}).json()["draft"]
    result = client.post(f"/api/v1/tools/dry-run/from-draft/{draft['draft_id']}")
    assert result.status_code == 200
    assert result.json()["status"] == "blocked"


def test_chat_suggests_dry_run_next_action():
    response = client.post("/api/v1/chat", json={"message": r"Conserte o bug no projeto C:\Dev\AIpinho"})
    assert response.status_code == 200
    actions = response.json()["next_actions"]
    assert any(action["type"] == "dry_run_preview" for action in actions)
    assert response.json()["preview_id"]

