from aipinho.services.validation.task_status_consistency_validator import TaskStatusConsistencyValidator
from validation_fixtures import valid_task_result, valid_task_run


def test_status_consistency_completed_requirements():
    assert not TaskStatusConsistencyValidator().validate(valid_task_run(), valid_task_result())


def test_status_consistency_partial_requires_limitations():
    run = valid_task_run("partial")
    result = valid_task_result("partial")
    result["limitations"] = []
    findings = TaskStatusConsistencyValidator().validate(run, result)
    assert any(item.code == "missing_limitations_when_partial" for item in findings)


def test_status_consistency_blocked_requires_reason():
    run = valid_task_run("blocked")
    run["blocked_reasons"] = []
    findings = TaskStatusConsistencyValidator().validate(run, valid_task_result("blocked"))
    assert any(item.code == "status_inconsistency" for item in findings)
