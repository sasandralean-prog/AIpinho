from fastapi.testclient import TestClient
from aipinho.main import app
from tests.maintenance_helpers import create_proposal
client = TestClient(app)

def test_repair_proposal_from_diagnosis():
    proposal = create_proposal(client)
    assert proposal["execution_performed"] is False
    assert proposal["evidence_refs"]

def test_repair_without_diagnosis_is_blocked():
    response = client.post("/api/v1/maintenance/repair/propose", json={"diagnosis_run_id":"missing","repair_type":"patch_plan_preview","summary":"x"})
    assert response.status_code == 409
