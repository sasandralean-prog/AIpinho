from aipinho.services.replay.collectors.artifact_snapshot_collector import ArtifactSnapshotCollector

def test_artifact_snapshot_collector_is_sanitized_and_side_effect_free():
    item = ArtifactSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "artifact"})
    assert item["collector_type"] == "artifact"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
