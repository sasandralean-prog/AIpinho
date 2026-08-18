from aipinho.schemas.governance.lifecycle import CanonicalPermission
from aipinho.services.governance.lifecycle.governance_lifecycle_service import GovernanceLifecycleService


def test_preview_rejects_generic_write_files() -> None:
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Crie arquivos.",
        source_channel="unit",
        requested_actions=["write_files"],
        operation_type="project_generation",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="plan_1",
        workspace_path=r"C:\Users\rafae\Documents\AIpinhoTestes",
        target_paths=[r"C:\Users\rafae\Documents\AIpinhoTestes\App"],
        context_ref="ctx",
        expected_outputs=["project_generation_result", "validation_result"],
        validation_plan={"checks": ["target_paths_match_preview"]},
        rollback_plan={"strategy": "revert"},
    )

    assert snapshot.policy.permission == CanonicalPermission.ASK
    assert snapshot.approval_gate.can_create_approval is False
    assert snapshot.approval_gate.reason_code.value == "PREVIEW_REJECTED_GENERIC_WRITE_ACTION"


def test_approval_preview_contains_target_files_and_plan() -> None:
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Crie pasta do projeto.",
        source_channel="unit",
        requested_actions=["create_directory"],
        operation_type="filesystem_create_directory",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="plan_1",
        plan_kind="concrete_file_operations",
        workspace_path=r"C:\Users\rafae\Documents\AIpinhoTestes",
        target_paths=[r"C:\Users\rafae\Documents\AIpinhoTestes\App"],
        context_ref="ctx",
        expected_outputs=["filesystem_operation", "validation_result"],
        validation_plan={"checks": ["target_paths_match_preview"]},
        rollback_plan={"strategy": "remove_created_directory_if_empty"},
        plan_payload={"concrete_file_operations": [{"action": "create_directory", "target_path": r"C:\Users\rafae\Documents\AIpinhoTestes\App"}]},
    )

    assert snapshot.preview_quality.status == "ready"
    assert snapshot.approval_gate.can_create_approval is True


def test_patch_preview_rejects_directory_target_without_concrete_diff(tmp_path) -> None:
    workspace = tmp_path / "App"
    workspace.mkdir()

    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Aplique patch governado.",
        source_channel="unit",
        requested_actions=["apply_patch"],
        operation_type="patch_request",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="plan_1",
        plan_kind="patch_plan",
        workspace_path=str(workspace),
        target_paths=[str(workspace)],
        context_ref="ctx",
        expected_outputs=["patch_result", "validation_result"],
        validation_plan={"checks": ["target_paths_match_preview"]},
        rollback_plan={"strategy": "revert"},
        plan_payload={
            "patch_plan": {
                "files_to_modify": [{"path": str(workspace), "purpose": "patch_target"}],
                "patch_operations": [{"operation": "apply_patch_after_approval", "target_path": str(workspace)}],
            }
        },
    )

    assert snapshot.preview_quality.status == "PREVIEW_REJECTED_NO_EXECUTABLE_PLAN"
    assert snapshot.approval_gate.can_create_approval is False
    assert snapshot.approval_gate.reason_code.value == "PREVIEW_REJECTED_NO_EXECUTABLE_PLAN"


def test_patch_preview_allows_file_target_with_concrete_diff(tmp_path) -> None:
    workspace = tmp_path / "App"
    workspace.mkdir()
    target = workspace / "main.py"
    target.write_text("print('old')\n", encoding="utf-8")

    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Aplique patch governado.",
        source_channel="unit",
        requested_actions=["apply_patch"],
        operation_type="patch_request",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="plan_1",
        plan_kind="patch_plan",
        workspace_path=str(workspace),
        target_paths=[str(target)],
        context_ref="ctx",
        expected_outputs=["patch_result", "validation_result"],
        validation_plan={"checks": ["target_paths_match_preview"]},
        rollback_plan={"strategy": "revert"},
        plan_payload={
            "patch_plan": {
                "files_to_modify": [
                    {
                        "path": str(target),
                        "original": "print('old')",
                        "replacement": "print('new')",
                    }
                ]
            }
        },
    )

    assert snapshot.preview_quality.status == "ready"
    assert snapshot.approval_gate.can_create_approval is True
