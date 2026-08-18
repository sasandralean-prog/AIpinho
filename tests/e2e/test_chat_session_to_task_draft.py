from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def _chat(message: str, session_id: str | None = None):
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    return response.json()


def test_new_session_case():
    response = client.post("/api/v1/sessions", json={"surface": "api"})
    assert response.status_code == 200
    session = response.json()["session"]
    assert session["session_id"]
    assert session["recent_messages"] == []
    assert session["active_task_draft_id"] is None


def test_chat_casual_with_session_case():
    payload = _chat("Bom dia, tudo certo?")
    assert payload["session_id"]
    assert payload["status"] == "ok"
    assert payload["intent"]["intent_type"] == "conversation"
    assert payload["task_draft_id"] is None


def test_self_analysis_no_task_draft_case():
    payload = _chat("Explique sua arquitetura atual")
    assert payload["status"] == "ok"
    assert payload["intent"]["intent_type"] == "self_analysis"
    assert payload["task_draft_id"] is None


def test_chat_report_no_artifact_case():
    payload = _chat("Faca um report final desta conversa")
    assert payload["status"] == "ok"
    assert payload["intent"]["intent_type"] == "in_chat_final_report"
    assert payload["task_draft_id"] is None
    assert "write_files" not in payload["policy"]["approval_required_for"]


def test_readonly_analysis_with_workspace_creates_draft_case():
    payload = _chat(r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada")
    assert payload["status"] == "preview"
    assert payload["task_draft_id"]
    draft = client.get(f"/api/v1/task-drafts/{payload['task_draft_id']}").json()["draft"]
    assert draft["contract_type"] == "readonly_analysis"
    assert "read_files" in draft["requested_actions"]
    assert "write_files" in draft["denied_actions"]
    assert draft["safe_to_execute"] is False
    assert draft["safe_to_preview"] is True


def test_readonly_analysis_without_workspace_needs_clarification_case():
    payload = _chat("Explique a arquitetura desse projeto")
    assert payload["status"] == "needs_clarification"
    assert payload["intent"]["requires_workspace"] is True
    assert payload["policy"]["safe_to_execute"] is False


def test_artifact_report_creates_non_executing_draft_case():
    payload = _chat("Salve um relatorio em reports/final.md")
    assert payload["status"] == "needs_clarification"
    assert payload["task_draft_id"]
    draft = client.get(f"/api/v1/task-drafts/{payload['task_draft_id']}").json()["draft"]
    assert draft["contract_type"] == "artifact_generation"
    assert "write_files" in draft["requested_actions"]
    assert draft["safe_to_execute"] is False


def test_patch_request_creates_non_executing_draft_case():
    payload = _chat(r"Conserte o bug no projeto C:\Dev\AIpinho")
    assert payload["status"] == "preview"
    assert payload["task_draft_id"]
    draft = client.get(f"/api/v1/task-drafts/{payload['task_draft_id']}").json()["draft"]
    assert draft["contract_type"] == "patch_request"
    assert "patch_preview" in draft["requested_actions"]
    assert "apply_patch" in draft["approval_required_for"]
    assert draft["safe_to_execute"] is False


def test_forbidden_root_blocks_draft_case():
    payload = _chat(r"Corrija C:\PinhoabacaxiAI")
    assert payload["status"] == "blocked"
    assert payload["task_draft_id"] is None
    assert payload["intent"]["workspace"]["protected"] is True


def test_ambiguity_case():
    payload = _chat("Arrume tudo")
    assert payload["status"] == "needs_clarification"
    assert payload["task_draft_id"]
    assert payload["next_actions"][0]["type"] == "clarify"


def test_session_continuity_chat_report_case():
    first = _chat(r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada")
    second = _chat("E agora gere um report no chat", first["session_id"])
    assert second["status"] == "ok"
    assert second["intent"]["intent_type"] == "in_chat_final_report"
    assert second["task_draft_id"] is None
    assert "write_files" not in second["policy"]["approval_required_for"]


def test_session_workspace_candidate_requires_confirmation_case():
    first = _chat(r"Use C:\Dev\AIpinho como projeto")
    second = _chat("Explique a arquitetura sem alterar nada", first["session_id"])
    assert second["status"] in {"needs_clarification", "preview"}
    if second["status"] == "needs_clarification":
        assert any(action["type"] in {"clarify", "provide_workspace"} for action in second["next_actions"])
    assert second["policy"]["safe_to_execute"] is False