from aipinho.services.maintenance.signal_collectors.model_signal_collector import ModelSignalCollector

def test_model_collector_returns_sanitized_structured_signal():
    values = ModelSignalCollector().collect({"source_ref": "model_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "model"
    assert "secretvalue" not in str(values[0].details)
