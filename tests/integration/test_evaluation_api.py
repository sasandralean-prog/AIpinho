from fastapi.testclient import TestClient

from aipinho.app_factory import create_app

client = TestClient(create_app())


def test_evaluation_status_endpoint_reports_enabled_validators():
    response = client.get("/api/v1/evaluation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["evaluation"]["enabled"] is True
    assert data["output_contract_validation"]["enabled"] is True
    assert data["safety_validation"]["enabled"] is True


def test_evaluation_model_response_endpoint_accepts_valid_json():
    response = client.post("/api/v1/evaluation/model-response", json={
        "model_response": {"content": "{\"findings\": [], \"limitations\": []}", "finish_reason": "stop", "real_inference": False},
        "output_contract": {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"]},
        "safety_envelope": {"rules": ["no_tools", "no_files"]},
        "purpose": "chat",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_evaluation_output_contract_endpoint():
    response = client.post("/api/v1/evaluation/output-contract", json={"content": "{\"findings\": []}", "output_contract": {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"]}})
    assert response.status_code == 200
    assert "limitations" in response.json()["missing_fields"]


def test_evaluation_safety_endpoint():
    response = client.post("/api/v1/evaluation/safety", json={"content": "api_key=abc123", "safety_envelope": {}, "policy_decision": {}})
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "abc123" not in str(response.json())


def test_evaluation_evidence_endpoint():
    response = client.post("/api/v1/evaluation/evidence", json={"content": "{\"findings\": [{\"summary\": \"x\"}], \"limitations\": []}", "output_contract": {"require_evidence": True}, "evidence_context": [{"evidence_id": "ev1"}]})
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_evaluation_retry_decision_endpoint():
    response = client.post("/api/v1/evaluation/retry-decision", json={"evaluation_id": "ev", "status": "needs_retry", "violations": ["invalid_json"], "truncation_detected": False})
    assert response.status_code == 200
    assert response.json()["should_retry"] is True
