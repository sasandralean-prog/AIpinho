from aipinho.services.replay.collectors.patch_snapshot_collector import PatchSnapshotCollector

def test_patch_snapshot_collector_is_sanitized_and_side_effect_free():
    item = PatchSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "patch"})
    assert item["collector_type"] == "patch"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
