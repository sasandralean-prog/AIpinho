from aipinho.services.replay.collectors.intent_snapshot_collector import IntentSnapshotCollector

def test_intent_snapshot_collector_is_sanitized_and_side_effect_free():
    item = IntentSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "intent"})
    assert item["collector_type"] == "intent"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
