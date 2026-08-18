from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_analysis_status_endpoint():
    response = client.get("/api/v1/analysis/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["write_enabled"] is False


def test_analysis_project_tree_context_and_report_endpoints(tmp_path):
    (tmp_path / "README.md").write_text("AIpinho", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    payload = {"workspace": str(tmp_path), "max_files": 3}

    tree = client.post("/api/v1/analysis/project/tree", json=payload)
    context = client.post("/api/v1/analysis/project/context", json=payload)
    report = client.post("/api/v1/analysis/project/report", json=payload)
    full = client.post("/api/v1/analysis/project", json=payload)

    assert tree.status_code == 200
    assert context.status_code == 200
    assert report.status_code == 200
    assert full.status_code == 200
    assert tree.json()["content_read"] is False
    assert context.json()["raw_log_exposed"] is False
    assert full.json()["write_enabled"] is False
    assert full.json()["patch_enabled"] is False
