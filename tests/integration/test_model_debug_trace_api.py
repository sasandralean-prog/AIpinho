from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def test_model_doctor_api_creates_trace_and_debug_api_reads_it():
    response = client.post("/api/v1/models/qwen2_5_coder_7b_q4_k_m/doctor", json={"include_trace": True})
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["trace_id"]
    trace_response = client.get(f"/api/v1/debug/traces/{result['trace_id']}")
    assert trace_response.status_code == 200
    assert trace_response.json()["trace"]["trace_id"] == result["trace_id"]
    timeline_response = client.get(f"/api/v1/debug/traces/{result['trace_id']}/timeline")
    assert timeline_response.status_code == 200
    assert timeline_response.json()["timeline"]
