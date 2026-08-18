from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def preview(prompt: str):
    response = TestClient(create_app()).post("/api/v1/intent/contract-preview", json={"prompt": prompt, "context": {}})
    assert response.status_code == 200
    return response.json()


def test_readonly_prompt_to_policy_preview():
    body = preview("Explique a arquitetura do projeto C:\\Dev\\AIpinho sem alterar nada")

    assert body["intent_map"]["intent_type"] == "readonly_analysis"
    assert "read_files" in body["policy_preview"]["allowed_actions"]


def test_artifact_prompt_to_policy_preview_needs_approval():
    body = preview("Salve um relatório em reports/final.md")

    assert body["intent_map"]["intent_type"] == "artifact_generation"
    assert "write_files" in body["policy_preview"]["approval_required_for"] or body["policy_preview"].get("safe_to_execute") is False


def test_forbidden_root_prompt_to_policy_preview_denied():
    body = preview("Corrija C:\\PinhoabacaxiAI")

    assert body["intent_map"]["workspace"]["protected"] is True
    assert body["policy_preview"]["safe_to_execute"] is False
    assert "read_files" not in body["policy_preview"].get("allowed_actions", [])


def test_chat_report_does_not_become_write_files():
    body = preview("Faça um report final desta conversa")

    assert body["intent_map"]["intent_type"] == "in_chat_final_report"
    assert "write_files" not in body["intent_map"]["requested_actions"]
    assert body["intent_map"]["output_intent"]["channel"] == "chat"