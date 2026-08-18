from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy_kernel"))
    monkeypatch.setenv("AIPINHO_SELF_HEALING_ROOT", str(tmp_path / "self_healing"))
    return TestClient(app)


def test_self_healing_status_and_scan_endpoints_are_structured(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    status = client.get("/api/v1/self-healing/status")
    assert status.status_code == 200
    assert status.json()["raw_default_visible"] is False
    assert status.json()["detectors_loaded"] >= 1

    scan = client.post("/api/v1/self-healing/scan", json={"persist": True})
    assert scan.status_code == 200
    assert scan.json()["raw_default_visible"] is False
    assert "candidates" in scan.json()


def test_state_consistency_scan_bridge_returns_candidates(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.post("/api/v1/dashboard/state-consistency/scan")
    assert response.status_code == 200
    body = response.json()
    assert "state_consistency" in body
    assert "self_healing_candidates" in body
    assert body["raw_default_visible"] is False
