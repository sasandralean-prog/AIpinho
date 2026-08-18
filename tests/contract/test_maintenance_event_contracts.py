import pytest
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.events.event_core import EventContractValidator, EventContractRegistryService

EVENTS = [
    "maintenance_run_created", "maintenance_diagnosis_started", "maintenance_diagnosis_completed",
    "maintenance_diagnosis_failed", "invariant_check_started", "invariant_check_completed",
    "invariant_violation_detected", "repair_proposal_created", "repair_proposal_blocked",
    "repair_handoff_created", "maintenance_patch_preview_created", "maintenance_config_preview_created",
    "maintenance_validation_plan_created", "maintenance_rollback_plan_created",
    "maintenance_lesson_candidate_created", "autocure_action_blocked", "autocure_requires_approval",
]

@pytest.mark.parametrize("event_type", EVENTS)
def test_maintenance_event_is_registered(event_type):
    request = EventPublishRequest(event_type=event_type, source_service="maintenance_plane", human_summary="Contract event.")
    assert EventContractValidator().validate(request).allowed is True

def test_unknown_maintenance_event_is_blocked():
    request = EventPublishRequest(event_type="maintenance_unknown", source_service="maintenance_plane", human_summary="Unknown.")
    result = EventContractValidator().validate(request)
    assert result.allowed is False
    assert "unknown_event_type" in result.reasons
