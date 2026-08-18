from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def _create_patch_preview():
    draft_response = client.post("/api/v1/task-drafts", json={"prompt": r"Conserte o bug no projeto C:\Dev\AIpinho"})
    assert draft_response.status_code == 200
    draft = draft_response.json()["draft"]
    preview_response = client.post("/api/v1/previews", json={"draft_id": draft["draft_id"]})
    assert preview_response.status_code == 200
    return draft, preview_response.json()["preview"]


def test_preview_api_creates_non_executing_preview():
    _, preview = _create_patch_preview()
    assert preview["status"] == "approval_required"
    assert preview["safe_to_execute"] is False
    assert "apply_patch" in preview["approval_required_for"]

    fetched = client.get(f"/api/v1/previews/{preview['preview_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["preview"]["preview_id"] == preview["preview_id"]

    events = client.get(f"/api/v1/previews/{preview['preview_id']}/events")
    assert events.status_code == 200
    assert events.json()["events"]


def test_approval_api_lifecycle_and_invalid_second_decision():
    draft, preview = _create_patch_preview()
    approval_response = client.post("/api/v1/approvals", json={"preview_id": preview["preview_id"], "reason": "teste"})
    assert approval_response.status_code == 200
    approval = approval_response.json()["approval"]
    assert approval["status"] == "pending"
    assert approval["execution_status"] == "not_executed"

    approved = client.post(f"/api/v1/approvals/{approval['approval_id']}/approve", json={"reason": "ok"})
    assert approved.status_code == 200
    assert approved.json()["decision"]["execution_status"] == "not_executed"
    assert approved.json()["approval"]["status"] == "approved"

    draft_after = client.get(f"/api/v1/task-drafts/{draft['draft_id']}")
    assert draft_after.status_code == 200
    assert draft_after.json()["draft"]["status"] == "approved_for_future_execution"

    repeated = client.post(f"/api/v1/approvals/{approval['approval_id']}/reject", json={"reason": "late"})
    assert repeated.status_code == 409


def test_readonly_preview_cannot_create_approval():
    draft_response = client.post("/api/v1/task-drafts", json={"prompt": r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada"})
    assert draft_response.status_code == 200
    draft = draft_response.json()["draft"]
    preview_response = client.post("/api/v1/previews", json={"draft_id": draft["draft_id"]})
    assert preview_response.status_code == 200
    preview = preview_response.json()["preview"]
    assert preview["status"] == "preview_ready"

    approval_response = client.post("/api/v1/approvals", json={"preview_id": preview["preview_id"]})
    assert approval_response.status_code == 409


def test_chat_response_exposes_actionable_approval_without_execution():
    response = client.post("/api/v1/chat", json={"message": r"Conserte o bug no projeto C:\Dev\AIpinho"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_approval"
    assert body["preview_id"]
    assert body["approval_id"]
    assert body["task_id"]
    assert body["policy"]["safe_to_execute"] is False
    assert any(action["type"] == "approve" and action["target_id"] == body["approval_id"] for action in body["next_actions"])
    assert any(action["type"] == "reject" and action["target_id"] == body["approval_id"] for action in body["next_actions"])
    assert body["contract_preview"]["runtime"]["status"] == "waiting_input"
