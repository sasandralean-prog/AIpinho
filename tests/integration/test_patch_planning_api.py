from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from patch_fixtures import patch_request, patch_workspace

client = TestClient(create_app())


def test_patch_planning_status_and_governed_apply_route():
    response = client.get("/api/v1/patch-plans/status")
    assert response.status_code == 200
    data = response.json()["patch_planning"]
    assert data["mode"] == "governed_apply_review"
    assert data["apply_enabled"] is True
    assert client.post("/api/v1/patch-plans/patch_plan_abcdef/apply").status_code == 404


def test_patch_planning_api_flow(tmp_path):
    workspace = patch_workspace(tmp_path)
    response = client.post("/api/v1/patch-plans", json=patch_request(workspace).model_dump())
    assert response.status_code == 200
    plan = response.json()["plan"]
    assert plan["apply_enabled"] is False
    assert plan["write_enabled"] is False
    plan_id = plan["plan_id"]
    assert client.get(f"/api/v1/patch-plans/{plan_id}").status_code == 200
    assert client.get(f"/api/v1/patch-plans/{plan_id}/diff").status_code == 200
    assert client.get(f"/api/v1/patch-plans/{plan_id}/risk").status_code == 200
    assert client.get(f"/api/v1/patch-plans/{plan_id}/evidence").status_code == 200
    assert client.post(f"/api/v1/patch-plans/{plan_id}/validate").status_code == 200


def test_patch_planning_api_blocks_missing_evidence_and_forbidden_root(tmp_path):
    workspace = patch_workspace(tmp_path)
    missing = client.post("/api/v1/patch-plans", json={"workspace": str(workspace), "affected_files": ["docs/note.md"]})
    assert missing.json()["plan"]["status"] == "blocked"
    forbidden = client.post("/api/v1/patch-plans", json={"workspace": "C:\\Windows", "affected_files": ["docs/note.md"]})
    assert forbidden.json()["plan"]["status"] == "blocked"
