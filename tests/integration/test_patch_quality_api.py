from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from patch_fixtures import patch_request, patch_workspace

client = TestClient(create_app())


def test_patch_quality_status_and_governed_apply_route():
    response = client.get("/api/v1/patch-quality/status")
    assert response.status_code == 200
    data = response.json()["patch_quality"]
    assert data["apply_enabled"] is True
    assert data["test_execution_enabled"] is False
    assert client.post("/api/v1/patch-quality/results/patch_quality_abcdef/apply").status_code == 404


def test_patch_quality_api_validates_plan_and_exposes_trace(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan_response = client.post("/api/v1/patch-plans", json=patch_request(workspace).model_dump())
    plan_id = plan_response.json()["plan"]["plan_id"]
    quality_response = client.post(f"/api/v1/patch-quality/validate-plan/{plan_id}")
    assert quality_response.status_code == 200
    quality = quality_response.json()["quality"]
    assert quality["apply_enabled"] is True
    assert quality["write_enabled"] is True
    assert client.get(f"/api/v1/patch-plans/{plan_id}/quality").status_code == 200
    assert client.get(f"/api/v1/patch-quality/results/{quality['quality_id']}/trace").status_code == 200


def test_patch_quality_api_rejects_dangerous_diff():
    diff = "--- a/config.yaml\n+++ b/config.yaml\n@@ -1 +1 @@\n-write_enabled: false\n+write_enabled: true\n"
    response = client.post("/api/v1/patch-quality/validate-diff", json={"diff_text": diff})
    assert response.status_code == 200
    assert response.json()["quality"]["status"] == "rejected"
