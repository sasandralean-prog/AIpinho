from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)
PROJECT_ROOT = "C:\\Dev\\AIpinho"


def test_reports_status_endpoint():
    response = client.get("/api/v1/reports/status")
    assert response.status_code == 200
    body = response.json()
    assert body["deterministic_reports_enabled"] is True
    assert body["write_report_enabled"] is False
    assert body["artifact_preview_enabled"] is True


def test_reports_project_get_evidence_and_preview_artifact():
    response = client.post("/api/v1/reports/project", json={"workspace": PROJECT_ROOT, "goal": "architecture_overview", "limits": {"max_findings": 10, "max_evidence_per_finding": 3, "max_report_chars": 10000}})
    assert response.status_code == 200
    body = response.json()
    assert body["write_enabled"] is False
    assert body["patch_enabled"] is False
    assert body["shell_enabled"] is False
    assert body["status"] in {"completed", "partial"}
    report_id = body["report"]["report_id"]
    assert body["report"]["findings"]
    assert all(item["evidence"] for item in body["report"]["findings"])

    fetched = client.get(f"/api/v1/reports/{report_id}")
    evidence = client.get(f"/api/v1/reports/{report_id}/evidence")
    preview = client.post("/api/v1/reports/project/preview-artifact", json={"report_id": report_id, "workspace": PROJECT_ROOT, "target_path": "reports/analysis.md"})

    assert fetched.status_code == 200
    assert evidence.status_code == 200
    assert evidence.json()["vectorstore_enabled"] is False
    assert preview.status_code == 200
    assert preview.json()["status"] == "preview_ready"
    assert preview.json()["safe_to_execute"] is False


def test_reports_forbidden_root_blocked_and_preview_forbidden_target():
    response = client.post("/api/v1/reports/project", json={"workspace": "C:\\PinhoabacaxiAI", "goal": "security_readonly"})
    assert response.status_code == 200
    body = response.json()
    assert body["write_enabled"] is False
    assert body["report"]["status"] in {"blocked", "partial", "degraded"}

    ok = client.post("/api/v1/reports/project", json={"workspace": PROJECT_ROOT})
    report_id = ok.json()["report"]["report_id"]
    preview = client.post("/api/v1/reports/project/preview-artifact", json={"report_id": report_id, "workspace": PROJECT_ROOT, "target_path": "C:\\PinhoabacaxiAI\\report.md"})
    assert preview.status_code == 200
    assert preview.json()["status"] == "blocked"
    assert preview.json()["preview"]["violations"]
