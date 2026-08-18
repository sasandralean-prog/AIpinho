from fastapi.testclient import TestClient

from aipinho.app_factory import create_app

client = TestClient(create_app())


def test_model_status_endpoint_reports_stub_only_runtime():
    response = client.get("/api/v1/models/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["real_inference_enabled"] is True
    assert data["components"]["providers"]["real_inference_enabled"] is True


def test_models_list_contains_stub_and_disabled_placeholder():
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    models = {model["model_id"]: model for model in data["models"]}
    compat_models = {model["model_id"]: model for model in data["compat_models"]}
    assert len(models) == 14
    assert models["qwen2_5_coder_7b_q4_k_m"]["default_coding_candidate"] is True
    assert compat_models["stub.default"]["enabled"] is True
    assert compat_models["llama.local.placeholder"]["enabled"] is False


def test_model_profile_capability_health_and_provider_endpoints():
    model_id = "qwen2_5_coder_7b_q4_k_m"
    assert client.get(f"/api/v1/models/{model_id}").status_code == 200
    assert client.get(f"/api/v1/models/{model_id}/profile").status_code == 200
    assert client.get(f"/api/v1/models/{model_id}/capabilities").json()["capabilities"]["detected_from"] == "config"
    assert client.get(f"/api/v1/models/{model_id}/health").json()["health"]["status"] in {"unknown", "healthy", "degraded", "blocked"}
    provider_payload = client.get("/api/v1/models/providers/llama_cpp_text").json()
    assert provider_payload["provider"]["auto_load_enabled"] is True
    assert provider_payload["runtime_enabled"] is True


def test_invoke_stub_endpoint_does_not_use_real_inference():
    response = client.post("/api/v1/models/invoke-stub", json={"prompt": "Ola", "output_contract_type": "chat_response"})
    assert response.status_code == 200
    data = response.json()["response"]
    assert data["real_inference"] is False
    assert data["provider_id"] == "stub.local"
    assert data["model_id"] == "stub.default"
    assert "No real LLM" in data["content"]
