from aipinho.schemas.supervisor.contracts import MonitorEvent
from aipinho.services.supervisor.monitor_event_service import MonitorEventService


def test_monitor_event_records_and_redacts(tmp_path):
    svc = MonitorEventService(path=tmp_path / "events.jsonl")
    svc.record(MonitorEvent(event_type="service_restarted", service_id="core_backend", port=9088, data={"authorization": "Bearer secret"}))
    events = svc.list_recent()
    assert events[0]["event_type"] == "service_restarted"
    assert events[0]["data"]["authorization"] == "[REDACTED_TOKEN]"
