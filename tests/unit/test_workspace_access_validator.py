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


def test_workspace_access_validator_ignores_declarative_forbidden_root_reference():
    run = valid_task_run()
    run["result"] = {
        "summary": "Do not access C:\\Windows; it is outside the authorized workspace.",
        "outputs": {
            "report": {
                "recommendation": "Never read or write C:\\Windows\\System32."
            }
        },
    }

    findings = WorkspaceAccessValidator().validate(run)

    assert not any(item.code == "forbidden_root_access" for item in findings)


def test_workspace_access_validator_blocks_operational_event_path():
    run = valid_task_run()
    run["events"] = [
        {
            "type": "tool_execution",
            "status": "blocked",
            "metadata": {"target_path": "C:\\Windows\\System32\\drivers\\etc\\hosts"},
        }
    ]

    findings = WorkspaceAccessValidator().validate(run)

    assert any(item.code == "forbidden_root_access" for item in findings)
