from fastapi.testclient import TestClient
from aipinho.main import app
from tests.maintenance_helpers import diagnosis_payload
client = TestClient(app)

def test_diagnose_requires_evidence_and_completes_readonly():
    rejected = client.post("/api/v1/maintenance/diagnose", json={}).json()
    assert rejected["status"] == "rejected"
    completed = client.post("/api/v1/maintenance/diagnose", json=diagnosis_payload({"requires_patch": True, "read_only": True})).json()
    assert completed["status"] == "completed"
    assert completed["run"]["side_effects_performed"] is False
