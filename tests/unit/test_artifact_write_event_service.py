from aipinho.services.artifacts.artifact_write_event_service import ArtifactWriteEventService


def test_event_service_creates_events():
    event = ArtifactWriteEventService().event("artifact_write_run_abcdef", "write_started", "Started")
    assert event.event_type == "write_started"
    assert event.write_run_id == "artifact_write_run_abcdef"
