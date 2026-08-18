from aipinho.services.replay.collectors.input_snapshot_collector import InputSnapshotCollector

def test_input_snapshot_collector_is_sanitized_and_side_effect_free():
    item = InputSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "input"})
    assert item["collector_type"] == "input"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
