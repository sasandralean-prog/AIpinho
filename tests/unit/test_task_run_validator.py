from aipinho.services.validation.task_run_validator import TaskRunValidator
from validation_fixtures import valid_events, valid_task_result, valid_task_run


def test_task_run_validator_accepts_valid_completed_run():
    findings = TaskRunValidator().validate(valid_task_run(), result=valid_task_result(), events=valid_events())
    assert not [item for item in findings if item.blocking]


def test_task_run_validator_rejects_completed_with_partial_required_step():
    run = valid_task_run("completed")
    run["plan"]["steps"][0]["status"] = "partial"
    findings = TaskRunValidator().validate(run, result=valid_task_result(), events=valid_events())
    assert any(item.code == "status_inconsistency" for item in findings)


def test_task_run_validator_requires_terminal_state():
    run = valid_task_run("completed")
    run["status"] = "running"
    findings = TaskRunValidator().validate(run, result=valid_task_result(), events=valid_events())
    assert any(item.code == "non_terminal_task_run" for item in findings)
