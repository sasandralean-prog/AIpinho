import json

from aipinho.services.debugger.debugger_sanitizer import DebuggerSanitizer
from aipinho.services.debugger.debugger_status_service import DebuggerStatusService
from aipinho.services.debugger.debugger_timeline_builder import DebuggerTimelineBuilder
from aipinho.services.debugger.debugger_trace_service_v2 import DebuggerTraceServiceV2
from aipinho.services.debugger.debugger_trace_store import DebuggerTraceStore


def test_debugger_status_is_read_only_and_hides_raw():
    status = DebuggerStatusService().status()

    assert status["status"] == "ok"
    assert status["workspace_write_enabled"] is False
    assert status["patch_apply_enabled"] is False
    assert status["shell_enabled"] is False
    assert status["raw_prompt_visible_by_default"] is False
    assert "model_run" in status["inspectors"]
    assert "rag_run" in status["inspectors"]


def test_debugger_sanitizer_hides_raw_and_truncates_long_text():
    sanitizer = DebuggerSanitizer()
    payload = {
        "raw_prompt": "do not show",
        "nested": {"raw_output": "secret", "visible": "ok"},
        "long": "x" * (sanitizer.MAX_TEXT + 20),
    }

    sanitized = sanitizer.sanitize(payload)

    assert sanitized["raw_prompt"] == "[HIDDEN_BY_DEBUGGER_POLICY]"
    assert sanitized["nested"]["raw_output"] == "[HIDDEN_BY_DEBUGGER_POLICY]"
    assert sanitized["nested"]["visible"] == "ok"
    assert sanitized["long"].endswith("...[TRUNCATED]")


def test_trace_service_and_timeline_return_sanitized_sorted_events(tmp_path):
    trace_id = "trace_sprint31_sorted"
    (tmp_path / f"{trace_id}.json").write_text(
        json.dumps(
            {
                "trace_id": trace_id,
                "category": "model",
                "events": [
                    {
                        "event_id": "event_late",
                        "event_type": "model_selected",
                        "category": "model",
                        "timestamp": "2026-06-08T12:00:02Z",
                        "summary": "late",
                        "data": {"raw_prompt": "hidden", "model_id": "small"},
                    },
                    {
                        "event_id": "event_early",
                        "event_type": "policy_checked",
                        "category": "policy",
                        "timestamp": "2026-06-08T12:00:01Z",
                        "summary": "early",
                        "data": {"ok": True},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    service = DebuggerTraceServiceV2(store=DebuggerTraceStore(tmp_path))

    trace = service.get(trace_id)
    timeline = DebuggerTimelineBuilder(service).build(trace_id)

    assert trace.status == "ok"
    assert trace.events[0].data["raw_prompt"] == "[HIDDEN_BY_DEBUGGER_POLICY]"
    assert [event.event_id for event in timeline.events] == ["event_early", "event_late"]
    assert timeline.sanitized is True


def test_missing_trace_returns_blocked_reason():
    trace = DebuggerTraceServiceV2(store=DebuggerTraceStore()).get("trace_missing_sprint31")

    assert trace.status == "missing"
    assert trace.blocked_reasons[0].code == "trace_not_found"
