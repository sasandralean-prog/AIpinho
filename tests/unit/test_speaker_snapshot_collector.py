from aipinho.services.replay.collectors.speaker_snapshot_collector import SpeakerSnapshotCollector

def test_speaker_snapshot_collector_is_sanitized_and_side_effect_free():
    item = SpeakerSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "speaker"})
    assert item["collector_type"] == "speaker"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
