from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def token_header():
    token = client.post("/api/v1/mobile/pairing/create-token").json()["pairing"]["token"]
    return {"Authorization": f"Bearer {token}"}

def test_service_supervisor_connectivity_layer_flow():
    headers = token_header()
    case_results = []
    monitor = client.get("/api/v1/monitor/status").json()["supervisor"]
    case_results.append(("supervisor_status", monitor["monitor_port"] == 9099))
    ports = client.get("/api/v1/monitor/ports").json()["ports"]
    case_results.append(("port_status", {p["port"] for p in ports} == {9080, 9088, 9089, 9098, 9099}))
    services = client.get("/api/v1/monitor/services").json()["services"]
    case_results.append(("manifest_services", len(services) == 5 and next(s for s in services if s["port"] == 9099)["restartable"] is False and next(s for s in services if s["port"] == 9080)["restartable"] is False))
    for sid in ["core_backend", "interaction_gateway", "artifact_service"]:
        case_results.append((f"restart_{sid}", client.post(f"/api/v1/monitor/services/{sid}/restart", json={}, headers=headers).json()["restart"]["allowed"] is True))
    case_results.append(("restart_monitor_blocked", client.post("/api/v1/monitor/services/monitor_supervisor/restart", json={}, headers=headers).json()["restart"]["allowed"] is False))
    case_results.append(("unknown_service_blocked", client.post("/api/v1/monitor/services/unknown/restart", json={}, headers=headers).json()["restart"]["allowed"] is False))
    case_results.append(("unknown_port_blocked", client.post("/api/v1/monitor/ports/12345/restart", json={}, headers=headers).json()["restart"]["allowed"] is False))
    case_results.append(("missing_token_unauthorized", client.post("/api/v1/monitor/services/core_backend/restart", json={}).status_code == 401))
    commands = client.get("/api/v1/connection/adb/reverse-commands").json()["adb_reverse"]["commands"]
    case_results.append(("adb_commands", len(commands) == 5 and commands[0].endswith("9080") and commands[-1].endswith("9099")))
    profiles = client.get("/api/v1/connection/profiles").json()["profiles"]
    case_results.append(("profiles", {p["profile_id"] for p in profiles} >= {"adb_reverse", "wifi_lan", "tailscale", "manual"}))
    case_results.append(("realtime_status", client.get("/api/v1/realtime/status").json()["port"] == 9089))
    case_results.append(("artifact_status", client.get("/api/v1/artifacts/status").json()["service"]["port"] == 9098))
    case_results.append(("human_health", bool(client.get("/api/v1/monitor/human-health").json()["messages"])))
    cfg = client.get("/api/v1/config/status").json()
    case_results.append(("config_status_has_supervisor", any("config/supervisor/service_manifest.yaml" in c["path"].replace("\\", "/") for c in cfg["configs"])))
    status = client.get("/api/v1/status").json()["components"]
    case_results.append(("status_components", status["monitor_port"] == 9099 and status["token_auth_enabled"] is True))
    case_results.append(("no_side_effects", status["local_model_chat_use_enabled"] is False and status["auto_ingest_enabled"] is False and status["legacy_vectorstore_enabled"] is False))
    assert all(ok for _, ok in case_results), case_results
