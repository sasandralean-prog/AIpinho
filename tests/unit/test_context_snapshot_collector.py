from aipinho.services.replay.collectors.context_snapshot_collector import ContextSnapshotCollector

def test_context_snapshot_collector_is_sanitized_and_side_effect_free():
    item = ContextSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "context"})
    assert item["collector_type"] == "context"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
