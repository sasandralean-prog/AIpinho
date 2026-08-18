from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_draft_preview_approval_future_execution_only_flow():
    draft_response = client.post("/api/v1/task-drafts", json={"prompt": r"Conserte o bug no projeto C:\Dev\AIpinho"})
    assert draft_response.status_code == 200
    draft = draft_response.json()["draft"]
    assert draft["safe_to_execute"] is False

    preview_response = client.post(f"/api/v1/previews/from-draft/{draft['draft_id']}")
    assert preview_response.status_code == 200
    preview = preview_response.json()["preview"]
    assert preview["status"] == "approval_required"
    assert preview["safe_to_execute"] is False

    approval_response = client.post("/api/v1/approvals", json={"preview_id": preview["preview_id"], "reason": "aprovar contrato futuro"})
    assert approval_response.status_code == 409
    assert approval_response.json()["detail"] in {
        "PREVIEW_REJECTED_NO_CONTEXT_REF",
        "approval_preview_missing_executable_plan",
        "approval_preview_not_executable",
    }

    final_draft = client.get(f"/api/v1/task-drafts/{draft['draft_id']}").json()["draft"]
    assert final_draft["status"] in {"approval_required", "approval_pending"}
    assert final_draft["safe_to_execute"] is False


def test_preview_blocks_forbidden_root_end_to_end():
    draft_response = client.post("/api/v1/task-drafts", json={"prompt": r"Corrija C:\Windows\System32"})
    assert draft_response.status_code == 200
    draft = draft_response.json()["draft"]
    assert draft["status"] == "blocked"

    preview_response = client.post(f"/api/v1/previews/from-draft/{draft['draft_id']}")
    assert preview_response.status_code == 200
    preview = preview_response.json()["preview"]
    assert preview["status"] == "blocked"

    approval_response = client.post("/api/v1/approvals", json={"preview_id": preview["preview_id"]})
    assert approval_response.status_code == 409
