from aipinho.services.replay.collectors.event_timeline_snapshot_collector import EventTimelineSnapshotCollector

def test_event_timeline_snapshot_collector_is_sanitized_and_side_effect_free():
    item = EventTimelineSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "event_timeline"})
    assert item["collector_type"] == "event_timeline"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
