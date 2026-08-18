from aipinho.services.validation.policy_compliance_validator import PolicyComplianceValidator
from validation_fixtures import valid_task_run


def test_policy_compliance_rejects_missing_snapshot():
    run = valid_task_run()
    run["policy_snapshot"] = {}
    findings = PolicyComplianceValidator().validate(run)
    assert any(item.code == "missing_policy_snapshot" for item in findings)


def test_policy_compliance_rejects_denied_policy():
    run = valid_task_run()
    run["policy_snapshot"]["status"] = "denied"
    findings = PolicyComplianceValidator().validate(run)
    assert any(item.code == "policy_denied_target" for item in findings)
