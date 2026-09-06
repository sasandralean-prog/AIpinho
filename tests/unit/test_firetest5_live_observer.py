from __future__ import annotations

from unittest.mock import patch

from tools.firetest5.live_observer import _compact_event, _events, _find_run_for_session, observe


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


def test_find_run_for_session_uses_exact_correlation() -> None:
    assert _find_run_for_session(
        {
            "sessions": [
                {"task_run_id": "task_run_other", "metadata": {"session_id": "other"}},
                {"task_run_id": "task_run_test", "metadata": {"session_id": "firetest"}},
            ]
        },
        "firetest",
    ) == "task_run_test"


def test_observer_acquires_task_run_independently_of_chat_response() -> None:
    observed_session = {"value": None}

    def fake_request(self, method: str, path: str, payload=None, *, timeout=None):  # noqa: ANN001
        if method == "GET" and path == "/api/v1/health":
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {"status": "ok"}}
        if method == "GET" and path in {"/api/v1/runtime/hygiene/queue-health", "/api/v1/task-runtime/queue"}:
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {}}
        if method == "POST" and path == "/api/v1/chat":
            observed_session["value"] = payload["session_id"]
            return {"ok": True, "status_code": 200, "elapsed_ms": 2, "body": {"status": "accepted_running"}}
        if method == "GET" and path.startswith("/api/v1/task_runs?session_id="):
            session_id = path.split("session_id=", 1)[1].split("&", 1)[0]
            return {
                "ok": True,
                "status_code": 200,
                "elapsed_ms": 1,
                "body": {
                    "sessions": [
                        {"task_run_id": "task_run_test", "metadata": {"session_id": session_id}}
                    ]
                },
            }
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
        if method == "GET" and path in {"/api/v1/runtime/doctor", "/api/v1/runtime-doctor/status"}:
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {}}
        raise AssertionError(f"unexpected request: {method} {path}")

    with patch("tools.firetest5.live_observer.ApiClient.request", new=fake_request):
        result = observe(timeout_seconds=2, poll_seconds=1)

    assert observed_session["value"] == result["correlation_session_id"]
    assert result["verdict"] == "TERMINAL_RUNTIME_OBSERVED"
    assert result["task_run_id"] == "task_run_test"
    assert result["chat"]["status"] == "accepted_running"
    assert result["acquisition"]["status"] == "task_run_acquired"
    assert len(result["pre_task_run_samples"]) >= 1
    assert len(result["samples"]) == 1


def test_observer_does_not_call_mutating_doctor_endpoints() -> None:
    called_methods: list[tuple[str, str]] = []

    def fake_request(self, method: str, path: str, payload=None, *, timeout=None):  # noqa: ANN001
        called_methods.append((method, path))
        if method == "GET" and path == "/api/v1/health":
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {"status": "ok"}}
        if method == "GET" and path in {"/api/v1/runtime/hygiene/queue-health", "/api/v1/task-runtime/queue"}:
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {}}
        if method == "POST" and path == "/api/v1/chat":
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {"task_run_id": "task_run_test"}}
        if method == "GET" and path.startswith("/api/v1/task_runs?session_id="):
            session_id = path.split("session_id=", 1)[1].split("&", 1)[0]
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {"sessions": [{"task_run_id": "task_run_test", "metadata": {"session_id": session_id}}]}}
        if method == "GET" and path.startswith("/api/v1/task-runs/task_run_test/"):
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {"status": "completed", "finished_at": "2026-09-06T00:00:00Z"}}
        if method == "GET" and path.startswith("/api/v1/task_runs/task_run_test/"):
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {"events": [{"type": "run_completed"}]}}
        if method == "GET" and path.startswith("/api/v1/runtime/operator/"):
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {}}
        if method == "GET" and path in {"/api/v1/runtime/doctor", "/api/v1/runtime-doctor/status"}:
            return {"ok": True, "status_code": 200, "elapsed_ms": 1, "body": {}}
        raise AssertionError(f"unexpected request: {method} {path}")

    with patch("tools.firetest5.live_observer.ApiClient.request", new=fake_request):
        result = observe(timeout_seconds=2, poll_seconds=1)

    assert result["verdict"] == "TERMINAL_RUNTIME_OBSERVED"
    assert result["task_run_id"] == "task_run_test"
    assert not any(
        method == "POST" and ("doctor" in path or "operator" in path)
        for method, path in called_methods
    )
