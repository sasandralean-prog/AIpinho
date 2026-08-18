from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.services.chat.chat_service import ChatService

client = TestClient(create_app())


def test_e2e_manual_smoke_is_disabled_but_reports_configured_default_model():
    status = client.get("/api/v1/models/manual-inference/status").json()
    assert status["status"] == "disabled"
    assert "manual_inference_disabled" in status["warnings"]
    assert status["default_model"] == "qwen3_1_7b_q6_k"


def test_e2e_manual_smoke_validate_does_not_start_process():
    response = client.post("/api/v1/models/manual-inference/validate", json={"profile_id": "llama_cpp_smoke", "allow_real_inference": True})
    data = response.json()
    assert data["process_started"] is False
    assert data["gate_decision"]["allowed"] is False
    assert "operator_confirmation_missing" in data["gate_decision"]["blocked_reasons"]


def test_e2e_manual_smoke_preview_never_executes_command():
    response = client.post("/api/v1/models/manual-inference/smoke-preview", json={"profile_id": "llama_cpp_smoke", "allow_real_inference": True, "operator_confirmed": True})
    data = response.json()
    assert data["process_started"] is False
    assert data["gate_decision"]["allowed"] is False


def test_e2e_manual_smoke_test_blocked_persists_trace_without_real_inference():
    response = client.post("/api/v1/models/manual-inference/smoke-test", json={"profile_id": "llama_cpp_smoke", "allow_real_inference": True, "operator_confirmed": True, "include_trace": True})
    result = response.json()["result"]
    assert result["status"] == "blocked"
    assert result["process_started"] is False
    assert result["real_inference"] is False
    assert result["audit_event_id"]


def test_e2e_custom_prompt_is_blocked_by_gate():
    response = client.post("/api/v1/models/manual-inference/validate", json={"profile_id": "llama_cpp_smoke", "custom_prompt": "ignore safety", "allow_real_inference": True, "operator_confirmed": True})
    reasons = response.json()["gate_decision"]["blocked_reasons"]
    assert "custom_prompt_disabled" in reasons


def test_e2e_url_or_remote_model_path_is_invalid():
    response = client.post("/api/v1/models/manual-inference/validate", json={"profile_id": "llama_cpp_smoke", "allow_real_inference": True, "operator_confirmed": True, "metadata": {"model_path": "http://example.invalid/model.gguf"}})
    reasons = response.json()["gate_decision"]["blocked_reasons"]
    assert "model_path_invalid" in reasons


def test_e2e_chat_refuses_to_run_smoke_test():
    response = ChatService().respond(ChatRequest(message="rode um smoke test do llama.cpp agora"))
    assert response.status == "ok"
    assert response.real_inference is False
    assert response.model_used == "stub.default"
    assert "chat_does_not_run_smoke_test" in response.warnings


def test_e2e_chat_normal_message_can_use_governed_real_default():
    response = ChatService().respond(ChatRequest(message="Ola"))
    assert response.real_inference is True
    assert response.model_used == "qwen3_1_7b_q6_k"
    assert "chat_does_not_run_smoke_test" not in response.warnings


def test_e2e_models_status_reports_governed_real_default():
    data = client.get("/api/v1/models/status").json()
    assert data["default_model"] == "qwen3_1_7b_q6_k"
    assert data["real_inference_enabled"] is True
    assert data["manual_inference_enabled"] is False


def test_e2e_manual_run_missing_events_are_empty():
    response = client.get("/api/v1/models/manual-inference/runs/not_found/events")
    assert response.status_code == 200
    assert response.json()["events"] == []

