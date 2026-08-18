from aipinho.services.replay.collectors.role_pipeline_snapshot_collector import RolePipelineSnapshotCollector

def test_role_pipeline_snapshot_collector_is_sanitized_and_side_effect_free():
    item = RolePipelineSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "role_pipeline"})
    assert item["collector_type"] == "role_pipeline"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
