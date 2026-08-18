from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "project_profiles"


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AIPINHO_PROJECT_PROFILES_ROOT", str(tmp_path / "project_profiles"))
    return TestClient(app)


def test_project_profiles_api_detect_create_validate_select_and_mobile_selector(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    detected = client.post("/api/v1/projects/profiles/detect", json={"root_path": str(FIXTURES / "android_gradle_project")})
    assert detected.status_code == 200
    candidate = detected.json()
    assert candidate["candidate"]["detected_stack"] == "android_gradle"
    assert candidate["proposed_profile"]["stack"] == "android_gradle"

    created = client.post("/api/v1/projects/profiles", json={"profile": candidate["proposed_profile"]})
    assert created.status_code == 200
    project_id = created.json()["profile"]["project_id"]

    listed = client.get("/api/v1/projects/profiles")
    assert listed.status_code == 200
    assert listed.json()["profiles"][0]["project_id"] == project_id

    validation = client.post(f"/api/v1/projects/profiles/{project_id}/validate")
    assert validation.status_code == 200
    assert validation.json()["validation"]["status"] in {"active", "needs_review"}

    selected = client.post(f"/api/v1/projects/profiles/{project_id}/select", json={})
    assert selected.status_code == 200
    assert selected.json()["selection"]["project_id"] == project_id

    mobile = client.get("/api/v1/mobile/view-model/projects")
    assert mobile.status_code == 200
    assert mobile.json()["active_project_id"] == project_id


def test_project_profile_secret_detection_returns_structured_error(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    detected = client.post("/api/v1/projects/profiles/detect", json={"root_path": str(FIXTURES / "project_with_fake_secret")})
    assert detected.status_code == 200

    created = client.post("/api/v1/projects/profiles", json={"profile": detected.json()["proposed_profile"]})
    assert created.status_code == 422
    assert created.json()["detail"] == "project_profile_secret_detected"
