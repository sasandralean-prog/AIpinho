from aipinho.services.maintenance.signal_collectors.debugger_signal_collector import DebuggerSignalCollector

def test_debugger_collector_returns_sanitized_structured_signal():
    values = DebuggerSignalCollector().collect({"source_ref": "debugger_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "debugger"
    assert "secretvalue" not in str(values[0].details)
