from aipinho.services.maintenance.signal_collectors.supervisor_signal_collector import SupervisorSignalCollector

def test_supervisor_collector_returns_sanitized_structured_signal():
    values = SupervisorSignalCollector().collect({"source_ref": "supervisor_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "supervisor"
    assert "secretvalue" not in str(values[0].details)
