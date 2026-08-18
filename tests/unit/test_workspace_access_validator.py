from aipinho.services.validation.workspace_access_validator import WorkspaceAccessValidator
from validation_fixtures import valid_task_run


def test_workspace_access_validator_blocks_forbidden_root():
    run = valid_task_run()
    run["workspace"] = "C:\\Windows\\System32"
    findings = WorkspaceAccessValidator().validate(run)
    assert any(item.code == "forbidden_root_access" for item in findings)


def test_workspace_access_validator_does_not_block_authorized_root():
    run = valid_task_run()
    run["workspace"] = "C:\\PinhoabacaxiAI"
    findings = WorkspaceAccessValidator().validate(run)
    assert not any(item.code == "forbidden_root_access" for item in findings)


def test_workspace_access_validator_detects_path_traversal():
    findings = WorkspaceAccessValidator().validate({"path": "..\\secret.txt"})
    assert any(item.code == "path_traversal_signal" for item in findings)


def test_workspace_access_validator_warns_workspace_needs_clarification():
    run = valid_task_run()
    run["workspace_snapshot"]["needs_clarification"] = True
    findings = WorkspaceAccessValidator().validate(run)
    assert any(item.code == "workspace_needs_clarification" for item in findings)
