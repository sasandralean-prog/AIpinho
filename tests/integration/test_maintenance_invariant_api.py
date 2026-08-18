from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def test_invariant_list_detail_and_check():
    listed = client.get("/api/v1/maintenance/invariants").json()
    assert listed["count"] == 15
    detail = client.get("/api/v1/maintenance/invariants/patch_never_with_read_only")
    assert detail.status_code == 200
    checked = client.post("/api/v1/maintenance/invariants/check", json={"signals":{"requires_patch":True,"read_only":True}}).json()
    assert checked["violations"][0]["severity"] == "critical"
