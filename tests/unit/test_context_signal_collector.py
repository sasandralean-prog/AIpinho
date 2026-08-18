from aipinho.services.maintenance.signal_collectors.context_signal_collector import ContextSignalCollector

def test_context_collector_returns_sanitized_structured_signal():
    values = ContextSignalCollector().collect({"source_ref": "context_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "context"
    assert "secretvalue" not in str(values[0].details)
