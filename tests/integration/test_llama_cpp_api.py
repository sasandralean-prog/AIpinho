from fastapi.testclient import TestClient

from aipinho.app_factory import create_app

client = TestClient(create_app())


def test_llama_cpp_status_endpoint_reports_runtime_without_execution():
    response = client.get("/api/v1/models/llama-cpp/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"available", "degraded"}
    assert data["enabled"] is True
    assert data["real_inference_enabled"] is True
    assert data["executable_valid"] is True


def test_llama_cpp_validate_null_paths_no_execution():
    response = client.post("/api/v1/models/llama-cpp/validate", json={"executable_path": None, "model_path": None})
    assert response.status_code == 200
    data = response.json()
    assert data["process_started"] is False
    assert data["environment"]["executable"]["configured"] is False
    assert data["environment"]["model"]["configured"] is False


def test_llama_cpp_estimate_endpoint_no_execution():
    response = client.post("/api/v1/models/llama-cpp/estimate", json={"ctx_size": 2048, "n_predict": 128})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["process_started"] is False


def test_llama_cpp_invoke_preview_disabled_no_execution():
    response = client.post("/api/v1/models/llama-cpp/invoke-preview", json={"prompt": "Ola"})
    assert response.status_code == 200
    data = response.json()
    assert data["process_started"] is False
    assert data["gate_decision"]["allowed"] is False
    assert data["command_preview"] is None


def test_llama_cpp_invoke_blocked_by_default_no_500():
    response = client.post("/api/v1/models/llama-cpp/invoke", json={"prompt": "Ola"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["process_started"] is False
    assert data["response"]["real_inference"] is False
