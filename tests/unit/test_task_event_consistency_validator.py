from aipinho.services.validation.task_event_consistency_validator import TaskEventConsistencyValidator
from validation_fixtures import valid_events


def test_event_consistency_accepts_valid_order():
    assert TaskEventConsistencyValidator().validate(valid_events()) == []


def test_event_consistency_rejects_completed_before_started():
    events = [{"type": "step_completed", "step_id": "step_1", "sequence": 1}]
    findings = TaskEventConsistencyValidator().validate(events)
    assert any(item.code == "event_order_invalid" for item in findings)


def test_event_consistency_rejects_duplicate_completion():
    events = [{"type": "step_started", "step_id": "s", "sequence": 1}, {"type": "step_completed", "step_id": "s", "sequence": 2}, {"type": "step_completed", "step_id": "s", "sequence": 3}]
    findings = TaskEventConsistencyValidator().validate(events)
    assert any(item.code == "duplicate_execution_signal" for item in findings)
