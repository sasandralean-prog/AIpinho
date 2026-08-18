
from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_legacy_rag_status_endpoint_contract():
    client = TestClient(create_app())
    response = client.get("/api/v1/legacy-rag/status")
    assert response.status_code == 200
    data = response.json()
    assert data["namespace_id"] == "legacy_pinhoabacaxi_curated"
    assert "namespace_committed" in data
