from fastapi.testclient import TestClient
from aipinho.main import app
from tests.maintenance_helpers import create_proposal
client = TestClient(app)

def test_validation_plan_never_runs_commands():
    proposal = create_proposal(client)
    body = client.post(f"/api/v1/maintenance/repair/{proposal['proposal_id']}/validation-plan").json()["validation"]
    assert body["checks"]
    assert body["execution_performed"] is False
