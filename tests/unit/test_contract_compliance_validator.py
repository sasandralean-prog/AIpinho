from aipinho.services.validation.contract_compliance_validator import ContractComplianceValidator
from validation_fixtures import valid_task_run


def test_contract_compliance_accepts_requested_subset():
    run = valid_task_run()
    run["requested_actions"] = ["read_files"]
    run["policy_snapshot"]["allowed_actions"] = ["read_files"]
    assert not ContractComplianceValidator().validate(run)


def test_contract_compliance_rejects_denied_action():
    run = valid_task_run()
    run["requested_actions"] = ["write_files"]
    run["policy_snapshot"]["allowed_actions"] = ["read_files"]
    run["policy_snapshot"]["denied_actions"] = ["write_files"]
    findings = ContractComplianceValidator().validate(run)
    assert any(item.code in {"denied_action_requested", "forbidden_contract_action", "action_outside_contract"} for item in findings)


def test_contract_compliance_requires_approval_for_approval_actions():
    run = valid_task_run()
    run["requested_actions"] = ["write_files"]
    run["policy_snapshot"]["allowed_actions"] = ["write_files"]
    run["policy_snapshot"]["approval_required_for"] = ["write_files"]
    findings = ContractComplianceValidator().validate(run)
    assert any(item.code == "approval_required_missing" for item in findings)


def test_contract_compliance_accepts_approved_actions_outside_initial_allow_list():
    run = valid_task_run()
    run["requested_actions"] = ["patch_preview", "apply_patch", "write_files"]
    run["policy_snapshot"]["allowed_actions"] = ["patch_preview"]
    run["policy_snapshot"]["approval_required_for"] = ["apply_patch", "write_files"]
    run["approval_id"] = "approval_test"

    findings = ContractComplianceValidator().validate(run)

    assert not any(item.code == "action_outside_contract" for item in findings)
    assert not any(item.code == "approval_required_missing" for item in findings)
