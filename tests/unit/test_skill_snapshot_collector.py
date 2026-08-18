from aipinho.services.replay.collectors.skill_snapshot_collector import SkillSnapshotCollector

def test_skill_snapshot_collector_is_sanitized_and_side_effect_free():
    item = SkillSnapshotCollector().collect({"token": "Bearer secretvalue", "source_ref": "skill"})
    assert item["collector_type"] == "skill"
    assert item["side_effects_performed"] is False
    assert "secretvalue" not in str(item)
