from types import SimpleNamespace

from fastapi.testclient import TestClient

from aipinho.main import create_app


class FakeRuntime:
    def __init__(self):
        self.run = SimpleNamespace(run_id="task_run_api", status="running")
        self.events = [
            SimpleNamespace(
                event_id="event_api",
                type="run_started",
                status="running",
                message="A execucao governada foi iniciada.",
                step_id=None,
                timestamp="2026-06-19T00:00:00+00:00",
            )
        ]

    def get_run(self, run_id):
        return self.run if run_id == self.run.run_id else None

    def get_events(self, _run_id):
        return self.events


def test_task_speaker_updates_endpoint_exposes_incremental_polling(monkeypatch):
    import aipinho.api.routers.task_runtime_router as router_module

    monkeypatch.setattr(router_module, "service", FakeRuntime())
    client = TestClient(create_app())

    response = client.get("/api/v1/task-runs/task_run_api/speaker/updates")

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_poll_seconds"] == 5
    assert payload["has_new_message"] is True
    assert payload["messages"][0]["text"] == "A execucao governada foi iniciada."
    assert payload["raw_included"] is False


def test_task_speaker_updates_endpoint_returns_structured_not_found(monkeypatch):
    import aipinho.api.routers.task_runtime_router as router_module

    monkeypatch.setattr(router_module, "service", FakeRuntime())
    client = TestClient(create_app())

    response = client.get("/api/v1/task-runs/missing/speaker/updates")

    assert response.status_code == 404
    assert response.json()["detail"] == "task_run_not_found"
