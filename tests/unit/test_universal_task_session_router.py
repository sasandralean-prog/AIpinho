from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers import task_runtime_router


class FakeUniversalSessions:
    def list_sessions(self, *, status=None, session_id=None, contract_type=None, limit=100):
        return [SimpleSession("task_run_11111111111111111111111111111111")]

    def get_session(self, run_id):
        return {
            "task_run_id": run_id,
            "status": "RUNNING",
            "phase": "write_file",
            "progress": {"percent": 50, "completed_units": 1, "total_units": 2, "basis": "task_run_plan_steps", "is_estimated": False},
        }

    def events(self, run_id, *, after_sequence=None, limit=200):
        return {"task_run_id": run_id, "events": [{"sequence": 2, "type": "running"}], "count": 1}

    def artifacts_for_run(self, run_id):
        return {"task_run_id": run_id, "artifact_state": {"status": "none", "count": 0, "artifact_ids": []}, "artifacts": [], "count": 0}

    def summary(self, run_id):
        return {"task_run_id": run_id, "status": "RUNNING", "phase": "write_file"}


class SimpleSession:
    def __init__(self, run_id):
        self.run_id = run_id

    def model_dump(self):
        return {"task_run_id": self.run_id, "status": "RUNNING"}


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr(task_runtime_router, "universal_sessions", FakeUniversalSessions())
    app = FastAPI()
    app.include_router(task_runtime_router.router)
    return TestClient(app)


def test_universal_task_session_endpoint(monkeypatch):
    client = _client(monkeypatch)

    response = client.get("/api/v1/task_runs/task_run_11111111111111111111111111111111")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_run_id"] == "task_run_11111111111111111111111111111111"
    assert payload["progress"]["basis"] == "task_run_plan_steps"


def test_universal_task_session_list_endpoint(monkeypatch):
    client = _client(monkeypatch)

    response = client.get("/api/v1/task_runs")

    assert response.status_code == 200
    assert response.json()["sessions"][0]["task_run_id"] == "task_run_11111111111111111111111111111111"


def test_universal_task_session_events_endpoint(monkeypatch):
    client = _client(monkeypatch)

    response = client.get("/api/v1/task_runs/task_run_11111111111111111111111111111111/events?after_sequence=1")

    assert response.status_code == 200
    assert response.json()["events"][0]["sequence"] == 2


def test_universal_task_session_summary_and_artifacts_endpoints(monkeypatch):
    client = _client(monkeypatch)

    summary = client.get("/api/v1/task_runs/task_run_11111111111111111111111111111111/summary")
    artifacts = client.get("/api/v1/task-runs/task_run_11111111111111111111111111111111/artifacts")

    assert summary.status_code == 200
    assert summary.json()["status"] == "RUNNING"
    assert artifacts.status_code == 200
    assert artifacts.json()["artifact_state"]["status"] == "none"
