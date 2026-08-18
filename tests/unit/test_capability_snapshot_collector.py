from aipinho.services.replay.collectors.capability_snapshot_collector import CapabilitySnapshotCollector

def test_capability_snapshot_collector_is_sanitized_and_side_effect_free():
    item = CapabilitySnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "capability"})
    assert item["collector_type"] == "capability"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
