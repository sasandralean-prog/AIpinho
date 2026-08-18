from aipinho.services.replay.collectors.maintenance_snapshot_collector import MaintenanceSnapshotCollector

def test_maintenance_snapshot_collector_is_sanitized_and_side_effect_free():
    item = MaintenanceSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "maintenance"})
    assert item["collector_type"] == "maintenance"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
