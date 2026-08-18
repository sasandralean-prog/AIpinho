from fastapi.testclient import TestClient
from aipinho.app_factory import create_app

def test_ux_polish_operational_hardening_flow():
    c=TestClient(create_app())
    assert c.get("/api/v1/ux/status").json()["features"]["raw_viewer_enabled"] is True
    assert c.get("/api/v1/ux/health").status_code==200
    assert c.get("/api/v1/events/search").status_code==200
    assert c.post("/api/v1/transfers/downloads",json={"artifact_id":"artifact_flow"}).status_code==200
