from aipinho.services.maintenance.anomaly_detector import AnomalyDetector

def test_detects_only_structured_violation_signals():
    values = AnomalyDetector().detect({"policy_violation": True, "normal": True})
    assert [item.signal_type for item in values] == ["policy_violation"]
