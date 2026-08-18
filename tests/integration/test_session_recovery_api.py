from fastapi.testclient import TestClient
from aipinho.app_factory import create_app
def test_session_recovery_api_round_trip():
    c=TestClient(create_app()); r=c.post("/api/v1/session/recovery/restore",json={"session_id":"s1","draft":"x"}); assert r.status_code==200; assert c.get("/api/v1/session/recovery").json()["draft"]=="x"
