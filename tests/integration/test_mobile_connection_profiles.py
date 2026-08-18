from fastapi.testclient import TestClient
from aipinho.app_factory import create_app
def test_connection_profiles_available():
    r=TestClient(create_app()).get("/api/v1/connection/profiles"); assert r.status_code in {200,401}
