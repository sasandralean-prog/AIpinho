from aipinho.services.maintenance.signal_collectors.policy_signal_collector import PolicySignalCollector

def test_policy_collector_returns_sanitized_structured_signal():
    values = PolicySignalCollector().collect({"source_ref": "policy_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "policy"
    assert "secretvalue" not in str(values[0].details)
