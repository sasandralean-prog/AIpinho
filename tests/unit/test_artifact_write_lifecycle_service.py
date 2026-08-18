from aipinho.services.artifacts.artifact_write_lifecycle_service import ArtifactWriteLifecycleService


def test_lifecycle_transitions_and_terminal_states():
    service = ArtifactWriteLifecycleService()
    assert service.can_transition("ready_to_execute", "running")
    assert not service.can_transition("completed", "running")
    assert service.is_terminal("blocked")
