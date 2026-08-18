from aipinho.services.replay.collectors.memory_snapshot_collector import MemorySnapshotCollector

def test_memory_snapshot_collector_is_sanitized_and_side_effect_free():
    item = MemorySnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "memory"})
    assert item["collector_type"] == "memory"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
