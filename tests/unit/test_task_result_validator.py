from aipinho.services.validation.task_result_validator import TaskResultValidator
from validation_fixtures import valid_task_result


def test_task_result_validator_accepts_safe_result():
    assert TaskResultValidator().validate(valid_task_result()) == []


def test_task_result_validator_requires_limitations_for_partial():
    result = valid_task_result("partial")
    result["limitations"] = []
    findings = TaskResultValidator().validate(result)
    assert any(item.code == "missing_limitations_when_partial" for item in findings)


def test_task_result_validator_rejects_unsafe_display():
    result = valid_task_result()
    result["safe_to_display"] = False
    findings = TaskResultValidator().validate(result)
    assert any(item.code == "unsafe_result_display" for item in findings)
