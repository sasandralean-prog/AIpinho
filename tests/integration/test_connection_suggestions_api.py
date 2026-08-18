from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_connection_suggestions_endpoint_is_read_only_api_v1() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/connection/suggestions")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["human_message"]
    assert payload["adb_reverse"]["commands"]
    assert "ports" in payload["wifi_lan"]
    assert "ports" in payload["tailscale"]
    assert payload["ports"]["bootstrap"] == 9080
    assert payload["ports"]["core_backend"] == 9088
    assert payload["ports"]["monitor"] == 9099
