from aipinho.services.maintenance.signal_collectors.rag_signal_collector import RagSignalCollector

def test_rag_collector_returns_sanitized_structured_signal():
    values = RagSignalCollector().collect({"source_ref": "rag_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "rag"
    assert "secretvalue" not in str(values[0].details)
