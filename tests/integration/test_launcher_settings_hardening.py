from fastapi.testclient import TestClient
from aipinho.app_factory import create_app

def client(): return TestClient(create_app())

def test_endpoint_ok(path="/api/v1/ux/status"):
    r=client().get(path); assert r.status_code==200
