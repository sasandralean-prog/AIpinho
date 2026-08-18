from aipinho.services.replay.collectors.rag_snapshot_collector import RagSnapshotCollector

def test_rag_snapshot_collector_is_sanitized_and_side_effect_free():
    item = RagSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "rag"})
    assert item["collector_type"] == "rag"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
