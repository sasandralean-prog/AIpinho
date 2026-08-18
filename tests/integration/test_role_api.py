from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_roles_endpoint_lists_safe_roles():
    response = client.get("/api/v1/roles")
    assert response.status_code == 200
    roles = response.json()["roles"]
    assert roles["speaker"]["can_call_tools"] is False
    assert roles["speaker"]["can_write"] is False


def test_role_effective_policy_endpoint():
    response = client.post("/api/v1/roles/analyst/effective-policy", json={"role_id": "analyst", "policy_decision": {"status": "allowed", "allowed_actions": ["read_files"], "denied_actions": ["write_files"]}})
    assert response.status_code == 200
    data = response.json()["effective_policy"]
    assert data["allowed"] is True
    assert data["can_call_tools"] is False


def test_role_model_gate_endpoint_blocks_real():
    response = client.post("/api/v1/roles/analyst/model-gate", json={"role_id": "analyst", "model_policy": "stub_only", "requested_model_id": "llama.local.placeholder", "output_contract": {"contract_type": "json_findings"}, "safety_envelope": {"rules": ["no_tools"]}})
    assert response.status_code == 200
    data = response.json()["model_gate"]
    assert data["allowed"] is False
    assert "real_inference_not_allowed_for_role_pipeline" in data["blocked_reasons"]


def test_role_run_pass_endpoint():
    response = client.post("/api/v1/roles/speaker/run-pass", json={"role_id": "speaker", "user_message": "Ola", "policy_decision": {"status": "allowed"}})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["tools_enabled"] is False
