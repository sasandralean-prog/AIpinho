from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.events.event_core import EventContractValidator

EVENTS=["replay_snapshot_created","replay_snapshot_sanitized","replay_case_created","replay_run_started","replay_run_completed","replay_run_failed","replay_diff_created","regression_candidate_created","regression_candidate_promoted","regression_case_created","regression_case_started","regression_case_completed","regression_case_failed","regression_suite_started","regression_suite_completed","regression_suite_failed","regression_failure_detected","golden_expectation_failed","regression_report_created"]

def test_replay_regression_events_are_registered_and_unknown_blocked():
    validator=EventContractValidator()
    assert all(validator.validate(EventPublishRequest(event_type=e, source_service="replay_harness" if e.startswith("replay_") else "regression_harness", human_summary="ok")).allowed for e in EVENTS)
    assert validator.validate(EventPublishRequest(event_type="replay_unknown", source_service="replay_harness", human_summary="bad")).allowed is False
