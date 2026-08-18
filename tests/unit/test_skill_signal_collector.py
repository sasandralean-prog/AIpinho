from aipinho.services.maintenance.signal_collectors.skill_signal_collector import SkillSignalCollector

def test_skill_collector_returns_sanitized_structured_signal():
    values = SkillSignalCollector().collect({"source_ref": "skill_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "skill"
    assert "secretvalue" not in str(values[0].details)
