from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_dashboard_view_model_has_cards_and_blocks_9099_restart():
    client = TestClient(create_app())

    response = client.get("/api/v1/mobile/view-model/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert data["state"]["screen"] == "dashboard"
    assert data["cards"]
    assert data["cards"][0]["card_id"] == "dashboard_backend_control"
    restart_backend = next(action for action in data["cards"][0]["safe_actions"] if action["action_id"] == "restart_core_backend")
    assert restart_backend["endpoint_ref"] == "/api/v1/backend-control/restart"
    assert restart_backend["side_effect"] is True
    restart_monitor = next(action for action in data["cards"][0]["safe_actions"] if action["action_id"] == "restart_monitor_9099_via_9080")
    assert restart_monitor["endpoint_ref"] == "/api/v1/bootstrap-control/monitor/restart"
    assert restart_monitor["side_effect"] is True
    port_9099 = next(card for card in data["cards"] if card["card_id"] == "dashboard_port_9099")
    restart = next(action for action in port_9099["safe_actions"] if action["action_id"] == "restart_monitor_9099_via_9080")
    assert restart["enabled"] is True
    assert restart["endpoint_ref"] == "/api/v1/bootstrap-control/monitor/restart"
    realtime = next(card for card in data["cards"] if card["card_id"] == "dashboard_realtime")
    assert realtime["status"] != "unknown"
    assert realtime["metadata"]["endpoint"] == "/api/v1/realtime/status"
    legacy_rag = next(card for card in data["cards"] if card["card_id"] == "dashboard_legacy_rag")
    assert legacy_rag["status"] == "historical"
    assert legacy_rag["severity"] == "info"
    maintenance = next(card for card in data["cards"] if card["card_id"] == "dashboard_maintenance")
    assert maintenance["status"] != "unknown"
    assert "Legacy RAG" not in "\n".join(data["state"]["warnings"])
    assert "Realtime/SSE: unknown" not in data["state"]["warnings"]
    assert "Maintenance/Regression: unknown" not in data["state"]["warnings"]
