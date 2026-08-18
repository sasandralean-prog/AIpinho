from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def test_mobile_pairing_api_create_rotate_verify_and_dev_config():
    created = client.post("/api/v1/mobile/pairing/create-token").json()["pairing"]
    assert created["token"]
    assert client.get("/api/v1/mobile/pairing/status").json()["pairing"]["plaintext_available"] is False
    assert client.post("/api/v1/mobile/pairing/verify", json={"token":created["token"], "device_id":"phone"}).json()["status"] == "verified"
    rotated = client.post("/api/v1/mobile/pairing/rotate-token").json()["pairing"]
    assert client.post("/api/v1/mobile/pairing/verify", json={"token":created["token"]}).json()["status"] == "invalid"
    assert client.post("/api/v1/mobile/pairing/verify", json={"token":rotated["token"]}).json()["status"] == "verified"
    assert client.get("/api/v1/mobile/dev-config").json()["token"] is None
