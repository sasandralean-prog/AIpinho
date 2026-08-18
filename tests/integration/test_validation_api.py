from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from validation_fixtures import report_missing_evidence, valid_report, valid_role_pipeline_run, valid_task_result

client = TestClient(create_app())


def request(target_type, payload=None, target_id=None):
    return {"target_type": target_type, "target_id": target_id, "payload": payload or {}}


def test_validation_status_endpoint():
    response = client.get("/api/v1/validation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["deterministic_only"] is True
    assert data["write_enabled"] is False


def test_validation_task_result_endpoint():
    response = client.post("/api/v1/validation/task-result", json=request("task_result", valid_task_result()))
    assert response.status_code == 200
    assert response.json()["status"] in {"passed", "passed_with_warnings"}


def test_validation_report_endpoint_rejects_missing_evidence():
    response = client.post("/api/v1/validation/report", json=request("project_report", report_missing_evidence()))
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_validation_side_effects_endpoint():
    response = client.post("/api/v1/validation/side-effects", json=request("side_effects", {"action": "apply_patch"}))
    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_validation_evidence_endpoint():
    response = client.post("/api/v1/validation/evidence", json=request("evidence", {"report": valid_report()}))
    assert response.status_code == 200
    assert response.json()["status"] in {"passed", "passed_with_warnings"}


def test_validation_results_and_trace_endpoints():
    created = client.post("/api/v1/validation/report", json=request("project_report", valid_report()))
    validation_id = created.json()["validation_id"]
    fetched = client.get(f"/api/v1/validation/results/{validation_id}")
    trace = client.get(f"/api/v1/validation/results/{validation_id}/trace")
    assert fetched.status_code == 200
    assert trace.status_code == 200


def test_validation_role_pipeline_endpoint_by_payload_fallback():
    response = client.post("/api/v1/validation", json=request("role_pipeline_run", valid_role_pipeline_run()))
    assert response.status_code == 200
