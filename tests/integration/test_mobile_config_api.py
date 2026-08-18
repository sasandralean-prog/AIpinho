from fastapi.testclient import TestClient
from aipinho.app_factory import create_app
def test_mobile_status_api():
    r=TestClient(create_app()).get("/api/v1/mobile/status"); assert r.status_code==200 and r.json()["android_app_enabled"]
