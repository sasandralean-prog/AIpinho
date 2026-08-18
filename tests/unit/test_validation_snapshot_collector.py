from aipinho.services.replay.collectors.validation_snapshot_collector import ValidationSnapshotCollector

def test_validation_snapshot_collector_is_sanitized_and_side_effect_free():
    item = ValidationSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "validation"})
    assert item["collector_type"] == "validation"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
