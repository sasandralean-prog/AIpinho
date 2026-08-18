from fastapi.testclient import TestClient
from aipinho.main import app
from tests.maintenance_helpers import create_diagnosis
client = TestClient(app)

def test_lesson_remains_candidate_not_memory():
    run = create_diagnosis(client)
    payload={"run_id":run["run_id"],"problem":"Observed issue","cause":"Candidate cause","evidence_refs":[run["diagnosis"]["evidence"][0]["evidence_id"]],"proposed_solution":"Review a governed change","expected_result":"Invariant restored","scope":"runtime","confidence":.8}
    body=client.post("/api/v1/maintenance/lessons/candidates",json=payload).json()["candidate"]
    assert body["status"]=="candidate"
    assert body["memory_mutation_performed"] is False
