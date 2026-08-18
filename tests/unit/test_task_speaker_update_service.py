from types import SimpleNamespace

from aipinho.services.speaker.task_speaker_update_service import TaskSpeakerUpdateService


class FakeRuntime:
    def __init__(self):
        self.run = SimpleNamespace(run_id="task_run_test", task_id="task_test", status="running")
        self.events = [
            SimpleNamespace(
                event_id="event_1",
                type="run_created",
                status="created",
                message="A task foi criada.",
                step_id=None,
                timestamp="2026-06-19T00:00:00+00:00",
            ),
            SimpleNamespace(
                event_id="event_2",
                type="step_started",
                status="running",
                message="A validacao foi iniciada.",
                step_id="validation",
                timestamp="2026-06-19T00:00:05+00:00",
            ),
        ]

    def get_run(self, run_id):
        return self.run if run_id == self.run.run_id else None

    def get_events(self, _run_id):
        return self.events


def test_speaker_updates_are_incremental_sanitized_and_poll_every_five_seconds():
    service = TaskSpeakerUpdateService(runtime=FakeRuntime())

    result = service.updates("task_run_test", after_event_id="event_1")

    assert result["next_poll_seconds"] == 5
    assert result["polling"]["recommended_interval_seconds"] == 5
    assert result["polling"]["cursor"] == "event_2"
    assert result["raw_included"] is False
    assert [message["source_event_ids"] for message in result["messages"]] == [["event_2"]]
    assert result["messages"][0]["text"] == "A validacao foi iniciada."
    assert result["messages"][0]["task_id"] == "task_test"
    assert result["messages"][0]["task_run_id"] == "task_run_test"


def test_speaker_updates_stop_polling_after_terminal_state():
    runtime = FakeRuntime()
    runtime.run.status = "completed"
    service = TaskSpeakerUpdateService(runtime=runtime)

    result = service.updates("task_run_test")

    assert result["polling"]["enabled"] is False


def test_speaker_updates_report_missing_run_structurally():
    service = TaskSpeakerUpdateService(runtime=FakeRuntime())

    try:
        service.updates("missing")
    except ValueError as exc:
        assert str(exc) == "task_run_not_found"
    else:
        raise AssertionError("missing run must fail")
