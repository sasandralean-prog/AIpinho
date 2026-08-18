from aipinho.services.maintenance.signal_collectors.event_signal_collector import EventSignalCollector

def test_event_collector_returns_sanitized_structured_signal():
    values = EventSignalCollector().collect({"source_ref": "event_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "event"
    assert "secretvalue" not in str(values[0].details)
