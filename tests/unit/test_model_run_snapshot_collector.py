from aipinho.services.replay.collectors.model_run_snapshot_collector import ModelRunSnapshotCollector

def test_model_run_snapshot_collector_is_sanitized_and_side_effect_free():
    item = ModelRunSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "model_run"})
    assert item["collector_type"] == "model_run"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
