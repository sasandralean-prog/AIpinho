from fastapi.testclient import TestClient

from aipinho.app_factory import create_app

client = TestClient(create_app())


def _payload(**overrides):
    payload = {
        "purpose": "chat",
        "role_id": "speaker",
        "user_message": "Me explique o que e Intent Map.",
        "output_contract_type": "chat_response",
    }
    payload.update(overrides)
    return payload


def test_prompt_status_endpoint_is_available():
    response = client.get("/api/v1/prompts/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_prompt_preview_endpoint_returns_model_request_without_invocation():
    response = client.post("/api/v1/prompts/preview", json=_payload(include_trace=True))
    assert response.status_code == 200
    preview = response.json()["preview"]
    assert preview["invokes_model"] is False
    assert preview["side_effects"] is False
    assert preview["model_request"]["model_id"] == "stub.default"


def test_prompt_budget_endpoint_reports_truncation_for_long_context():
    long_context = {"source_type": "file", "title": "large", "content": "x" * 30000, "priority": 1.0}
    response = client.post("/api/v1/prompts/estimate-budget", json=_payload(context_items=[long_context]))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["budget"]["truncated"] is True


def test_output_contract_validation_endpoint_detects_invalid_json():
    response = client.post("/api/v1/prompts/validate-output-contract", json={"contract_type": "json_findings", "content": "not json"})
    assert response.status_code == 200
    data = response.json()
    assert data["validation"]["valid"] is False
