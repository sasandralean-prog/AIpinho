from __future__ import annotations

from unittest.mock import patch

from tools.firetest5.live_observer import _compact_event, _events, observe


def test_events_accepts_events_and_timeline_shapes() -> None:
    assert _events({"events": [{"type": "run_completed"}]}) == [{"type": "run_completed"}]
    assert _events({"timeline": {"items": [{"type": "run_blocked"}]}}) == [{"type": "run_blocked"}]


def test_compact_event_preserves_firetest_checkpoint_semantics() -> None:
    compact = _compact_event(
        {
            "sequence": 7,
            "type": "artifact_render_checkpoint",
            "metadata": {
                "stage": "after_perception_payload_compile",
                "logical_path": "reports/firetest5/music_inventory.csv",
                "reason_code": "MEDIA_CAPABILITY_EXTENSION_NOT_DECLARED_BY_BACKENDS",
                "payload_metrics": {"rows": 84},
            },
        }
    )
    assert compact["sequence"] == 7
    assert compact["type"] == "artifact_render_checkpoint"
    assert compact["stage"] == "after_perception_payload_compile"
    assert compact["logical_path"] == "reports/firetest5/music_inventory.csv"
    assert compact["reason_code"] == "MEDIA_CAPABILITY_EXTENSION_NOT_DECLARED_BY_BACKENDS"
    assert compact["payload_metrics"] == {"rows": 84}


def test_observer_does_not_call_mutating_doctor_endpoints() -> None:
    responses = {
        ("GET", "/api/v1/health"): {"status_code": 200, "body": {"status": "ok"}},
        ("GET", "/api/v1/runtime/hygiene/queue-health"): {"status_code": 200, "body": {}},
        ("GET", "/api/v1/task-runtime/queue"): {"status_code": 200, "body": {}},
        ("POST", "/api/v1/chat"): {"status_code": 200, "body": {"task_run_id": "task_run_test"}},
    }

    def fake_request(self, method: str, path: str, payload=None):  # noqa: ANN001
        if (method, path) in responses:
            return {"ok": True, "elapsed_ms": 1, **responses[(method, path)]}
        if method == "GET" and path.startswith("/api/v1/task-runs/task_run_test/"):
            return {
                "ok": True,
                "status_code": 200,
                "elapsed_ms": 1,
                "body": {"status": "completed", "finished_at": "2026-09-06T00:00:00Z"},
            }
        if method == "GET" and path.startswith("/api/v1/task_runs/task_run_test/"):
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {"events": [{"type": "run_completed"}]}}
        if method == "GET" and path.startswith("/api/v1/runtime/operator/"):
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {}}
        if method == "GET" and path == "/api/v1/runtime/doctor":
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {}}
        if method == "GET" and path == "/api/v1/runtime-doctor/status":
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {}}
        raise AssertionError(f"unexpected request: {method} {path}")

    with patch("tools.firetest5.live_observer.ApiClient.request", new=fake_request):
        result = observe(timeout_seconds=2, poll_seconds=1)

    assert result["verdict"] == "TERMINAL_RUNTIME_OBSERVED"
    assert result["chat"]["task_run_id"] == "task_run_test"
    assert len(result["samples"]) == 1
