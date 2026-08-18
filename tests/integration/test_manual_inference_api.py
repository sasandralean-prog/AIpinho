from fastapi.testclient import TestClient

from aipinho.app_factory import create_app

client = TestClient(create_app())


def test_manual_inference_status_endpoint_is_disabled_by_default():
    response = client.get("/api/v1/models/manual-inference/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "disabled"
    assert data["manual_inference_enabled"] is False
    assert data["smoke_test_enabled"] is False
    assert data["chat_auto_real_inference"] is False


def test_manual_inference_profiles_endpoint_lists_manual_profiles():
    response = client.get("/api/v1/models/manual-inference/profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["profiles"]
    assert all(profile["manual_only"] is True for profile in data["profiles"])


def test_manual_inference_validate_blocks_without_process():
    response = client.post("/api/v1/models/manual-inference/validate", json={"profile_id": "llama_cpp_smoke"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["process_started"] is False
    assert data["gate_decision"]["allowed"] is False


def test_manual_inference_preview_blocks_without_process():
    response = client.post("/api/v1/models/manual-inference/smoke-preview", json={"profile_id": "llama_cpp_smoke"})
    assert response.status_code == 200
    data = response.json()
    assert data["process_started"] is False
    assert data["gate_decision"]["allowed"] is False
    assert data["command_preview"] is None


def test_manual_inference_smoke_test_blocked_run_is_auditable():
    response = client.post("/api/v1/models/manual-inference/smoke-test", json={"profile_id": "llama_cpp_smoke", "include_trace": True})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    result = data["result"]
    assert result["process_started"] is False
    assert result["real_inference"] is False
    assert result["audit_event_id"]

    run_response = client.get(f"/api/v1/models/manual-inference/runs/{result['run_id']}")
    assert run_response.status_code == 200
    assert run_response.json()["run"]["run_id"] == result["run_id"]

    events_response = client.get(f"/api/v1/models/manual-inference/runs/{result['run_id']}/events")
    assert events_response.status_code == 200
    assert events_response.json()["events"]


def test_manual_inference_missing_run_returns_404():
    response = client.get("/api/v1/models/manual-inference/runs/not_found")
    assert response.status_code == 404

