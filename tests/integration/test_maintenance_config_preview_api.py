from fastapi.testclient import TestClient
from aipinho.main import app
from tests.maintenance_helpers import create_proposal
client = TestClient(app)

def test_config_preview_never_writes():
    proposal = create_proposal(client, "config_change_preview")
    body = client.post(f"/api/v1/maintenance/repair/{proposal['proposal_id']}/config-preview").json()["preview"]
    assert body["write_performed"] is False
