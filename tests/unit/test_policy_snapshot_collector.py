from aipinho.services.replay.collectors.policy_snapshot_collector import PolicySnapshotCollector

def test_policy_snapshot_collector_is_sanitized_and_side_effect_free():
    item = PolicySnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "policy"})
    assert item["collector_type"] == "policy"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
