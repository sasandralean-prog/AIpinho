from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.services.runtime.readonly_task_step_runner import TaskStepOutcome
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


class CompletingExecutor:
    def execute_step(self, run, step, context):
        return TaskStepOutcome(status="completed", summary={"safe": step.step_type})


def api_payload():
    return {
        "source_type": "direct",
        "session_id": "session_api",
        "contract_type": "in_chat_final_report",
        "intent_map": {"intent_type": "in_chat_final_report"},
        "policy_decision": {"status": "allowed", "approval_required_for": []},
        "requested_actions": [],
        "start_immediately": True,
    }


def test_task_runtime_api_create_start_events_trace_and_result(monkeypatch, task_runtime_store):
    import aipinho.api.routers.task_runtime_router as router_module

    service = TaskRuntimeService(store=task_runtime_store)
    service.loop.executor = CompletingExecutor()
    monkeypatch.setattr(router_module, "service", service)
    client = TestClient(create_app())

    created = client.post("/api/v1/task-runs", json=api_payload())
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    assert created.json()["status"] == "queued"
    assert created.json()["auto_run_requested"] is True

    started = client.post(f"/api/v1/task-runs/{run_id}/start")
    assert started.status_code == 200
    assert started.json()["run"]["status"] == "completed"

    events = client.get(f"/api/v1/task-runs/{run_id}/events")
    timeline = client.get(f"/api/v1/task-runs/{run_id}/timeline")
    trace = client.get(f"/api/v1/task-runs/{run_id}/trace")
    result = client.get(f"/api/v1/task-runs/{run_id}/result")

    assert events.status_code == 200
    assert timeline.status_code == 200
    assert timeline.json()["task_run_id"] == run_id
    assert timeline.json()["sequence_contiguous"] is True
    assert timeline.json()["completion"]["terminal_event_id"]
    assert trace.status_code == 200
    assert result.status_code == 200
    assert result.json()["safe_to_display"] is True


def test_task_runtime_queue_endpoint_exposes_counts(monkeypatch, task_runtime_store):
    import aipinho.api.routers.task_runtime_router as router_module

    service = TaskRuntimeService(store=task_runtime_store)
    monkeypatch.setattr(router_module, "service", service)
    client = TestClient(create_app())

    client.post("/api/v1/task-runs", json=api_payload())
    response = client.get("/api/v1/task-runtime/queue")

    assert response.status_code == 200
    snapshot = response.json()["snapshot"]
    assert snapshot["total_visible"] == 1
    assert snapshot["pending_count"] == 1


def test_task_runtime_api_cancel_created_run(monkeypatch, task_runtime_store):
    import aipinho.api.routers.task_runtime_router as router_module

    service = TaskRuntimeService(store=task_runtime_store)
    monkeypatch.setattr(router_module, "service", service)
    client = TestClient(create_app())

    created = client.post("/api/v1/task-runs", json=api_payload())
    run_id = created.json()["run_id"]
    cancelled = client.post(f"/api/v1/task-runs/{run_id}/cancel", json={"reason": "test"})

    assert cancelled.status_code == 200
    assert cancelled.json()["cancellation_requested"] is True
    assert client.get(f"/api/v1/task-runs/{run_id}").json()["status"] == "cancelled"


def test_task_runtime_invalid_dynamic_id_returns_structured_not_found():
    client = TestClient(create_app())

    invalid = client.get("/api/v1/task-runs/status")
    official = client.get("/api/v1/task-runtime/status")

    assert invalid.status_code == 404
    assert invalid.json()["detail"] == "invalid_task_run_id"
    assert official.status_code == 200
