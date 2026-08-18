from aipinho.services.maintenance.signal_collectors.speaker_signal_collector import SpeakerSignalCollector

def test_speaker_collector_returns_sanitized_structured_signal():
    values = SpeakerSignalCollector().collect({"source_ref": "speaker_unit", "summary": "Observed signal.", "token": "Bearer secretvalue"})
    assert values[0].signal_type == "speaker"
    assert "secretvalue" not in str(values[0].details)
