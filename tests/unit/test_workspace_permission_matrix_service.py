from __future__ import annotations

from pathlib import Path

import yaml

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.services.runtime.runtime_profile_service import RuntimeProfileService
from aipinho.services.runtime.task_run_guard import TaskRunGuard


def _registry(path: Path, workspaces: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schema_version": 1, "workspaces": workspaces}, sort_keys=False), encoding="utf-8")
    return path


def test_permission_matrix_longest_path_and_deny_override(tmp_path: Path) -> None:
    root = tmp_path / "root"
    child = root / "child"
    registry = _registry(
        tmp_path / "workspace_registry.yaml",
        [
            {"workspace_id": "root", "root_path": str(root), "role": "target_mutable"},
            {"workspace_id": "child", "root_path": str(child), "role": "source_readonly"},
        ],
    )
    service = WorkspacePermissionMatrixService(registry).load()

    decision = service.decide(path=str(child / "file.txt"), permission="modify_file")

    assert decision.status == "denied"
    assert decision.workspace_id == "child"
    assert decision.reason_code == "permission_denied"


def test_permission_matrix_ask_requires_approval_for_target_write(tmp_path: Path) -> None:
    root = tmp_path / "target"
    registry = _registry(tmp_path / "workspace_registry.yaml", [{"workspace_id": "target", "root_path": str(root), "role": "target_mutable"}])
    service = WorkspacePermissionMatrixService(registry).load()

    decision = service.decide(path=str(root / "file.txt"), permission="create_file")

    assert decision.status == "approval_required"
    assert decision.reason_code == "permission_requires_approval"


def test_permission_matrix_disabled_workspace_denies(tmp_path: Path) -> None:
    root = tmp_path / "target"
    registry = _registry(
        tmp_path / "workspace_registry.yaml",
        [{"workspace_id": "target", "root_path": str(root), "role": "target_mutable", "enabled": False}],
    )
    service = WorkspacePermissionMatrixService(registry).load()

    decision = service.decide(path=str(root / "file.txt"), permission="read_file")

    assert decision.status == "denied"
    assert decision.reason_code == "workspace_disabled"


def test_permission_matrix_unregistered_workspace_denies(tmp_path: Path) -> None:
    registry = _registry(tmp_path / "workspace_registry.yaml", [])
    service = WorkspacePermissionMatrixService(registry).load()

    decision = service.decide(path=str(tmp_path / "outside" / "file.txt"), permission="read_file")

    assert decision.status == "denied"
    assert decision.reason_code == "workspace_not_registered"


def test_runtime_guard_uses_permission_matrix_for_denied_write(tmp_path: Path) -> None:
    source = tmp_path / "source"
    registry = _registry(tmp_path / "workspace_registry.yaml", [{"workspace_id": "source", "root_path": str(source), "role": "source_readonly"}])
    protected = tmp_path / "protected.yaml"
    protected.write_text("protected_roots: []\n", encoding="utf-8")
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir()
    (profiles_root / "write_file.yaml").write_text(
        yaml.safe_dump(
            {
                "profile": {
                    "id": "write_file",
                    "operation_types": ["governed_file_write"],
                    "workspace_requirements": {"required": True},
                    "allowed_actions": ["write_files"],
                    "steps": [],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    run = TaskRun(
        run_id="task_run_matrix",
        source_type="test",
        workspace=str(source),
        contract_type="filesystem_write",
        operation_type="governed_file_write",
        requested_actions=["write_files"],
        policy_snapshot={"status": "allowed", "allowed_actions": ["write_files"]},
        plan=TaskRunPlan(
            plan_id="plan_matrix",
            contract_type="filesystem_write",
            steps=[TaskRunStep(step_id="step_1", step_type="write_file", action="write_files")],
        ),
    )
    guard = TaskRunGuard(
        workspace_policy=WorkspacePolicyService(config_path=protected).load(),
        workspace_roles=WorkspaceRoleContractService(config_path=registry).load(),
        permission_matrix=WorkspacePermissionMatrixService(registry).load(),
        approvals=ApprovalService(store=ApprovalStore(root=tmp_path / "approvals")),
        profiles=RuntimeProfileService(profiles_root=profiles_root).load(),
    )

    decision = guard.check_run(run)

    assert decision.allowed is False
    assert "permission_denied:write_files" in decision.blocked_reasons

