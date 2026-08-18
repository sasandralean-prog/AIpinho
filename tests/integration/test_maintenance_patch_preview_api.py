from fastapi.testclient import TestClient
from aipinho.main import app
from tests.maintenance_helpers import create_proposal
client = TestClient(app)

def test_patch_preview_never_applies():
    proposal = create_proposal(client)
    body = client.post(f"/api/v1/maintenance/repair/{proposal['proposal_id']}/patch-preview").json()["preview"]
    assert body["delegated_to"] == "patch_planning_pipeline"
    assert body["apply_performed"] is False
