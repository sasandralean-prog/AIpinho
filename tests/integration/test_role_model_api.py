from fastapi.testclient import TestClient

from aipinho.app_factory import create_app

client = TestClient(create_app())


def test_role_model_status_endpoint_reports_controlled_runtime():
    response = client.get("/api/v1/role-models/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["chat_auto_role_inference"] is True
    assert data["default_coding_model"] == "qwen2_5_coder_7b_q4_k_m"


def test_role_model_list_and_gate_endpoints_are_ordered_before_role_id_routes():
    list_response = client.get("/api/v1/role-models")
    runs_response = client.get("/api/v1/role-models/runs")
    gate_response = client.get("/api/v1/role-models/coder/gate")

    assert list_response.status_code == 200
    assert runs_response.status_code == 200
    assert gate_response.status_code == 200
    assert gate_response.json()["gate"]["selected_model_id"] == "qwen2_5_coder_7b_q4_k_m"


def test_role_model_preview_does_not_invoke_model():
    response = client.post("/api/v1/role-models/coder/preview", json={"role_id": "coder", "prompt": "Revise sem executar ferramentas."})

    assert response.status_code == 200
    data = response.json()
    assert data["model_invoked"] is False
    assert data["side_effects"] is False
    assert data["result"]["real_inference_attempted"] is False


def test_role_model_run_attempts_real_runtime_then_uses_safe_fallback_when_unavailable():
    response = client.post("/api/v1/role-models/coder/run", json={"role_id": "coder", "prompt": "Explique um risco de codigo sem alterar arquivos."})

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["selected_model_id"] == "qwen2_5_coder_7b_q4_k_m"
    assert result["real_inference_attempted"] is True
    assert result["real_inference_completed"] is False
    assert result["fallback_used"] is True
    assert result["side_effects"] is False
    assert result["raw_output_hidden"] is True


def test_role_model_escalate_preview_requires_manual_confirmation():
    response = client.post("/api/v1/role-models/coder/escalate-preview", json={"role_id": "coder", "prompt": "Use 14B."})

    assert response.status_code == 200
    gate = response.json()["gate"]
    assert gate["allowed"] is False
    assert "operator_confirmation_required" in gate["blocked_reasons"]
