from fastapi.testclient import TestClient
from aipinho.main import app
from tests.maintenance_helpers import create_diagnosis, create_proposal

client = TestClient(app)

def test_supervised_autocure_full_preview_flow():
    status=client.get("/api/v1/maintenance/status").json()
    assert status["autonomous_apply"] is False
    run=create_diagnosis(client,{"speaker_claims_operation_completed":True,"completion_event_present":False,"source_refs":["event_e2e"]})
    assert run["violations"][0]["invariant_id"]=="speaker_no_false_progress"
    proposal=create_proposal(client)
    proposal_id=proposal["proposal_id"]
    patch=client.post(f"/api/v1/maintenance/repair/{proposal_id}/patch-preview").json()["preview"]
    config=client.post(f"/api/v1/maintenance/repair/{proposal_id}/config-preview").json()["preview"]
    validation=client.post(f"/api/v1/maintenance/repair/{proposal_id}/validation-plan").json()["validation"]
    rollback=client.post(f"/api/v1/maintenance/repair/{proposal_id}/rollback-plan").json()["rollback"]
    handoff=client.post(f"/api/v1/maintenance/repair/{proposal_id}/handoff").json()["handoff"]
    assert patch["apply_performed"] is False
    assert config["write_performed"] is False
    assert validation["execution_performed"] is False
    assert rollback["execution_performed"] is False
    assert handoff["execution_performed"] is False
    assert handoff["approval"]["approval_required"] is True
