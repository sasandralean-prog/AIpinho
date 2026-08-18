from __future__ import annotations

from pathlib import Path

import yaml

from aipinho.schemas.workspace_flows.workspace_flow import WorkspaceFlowEndpoint, WorkspaceFlowPlanRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.workspace_flows.workspace_flow_service import WorkspaceFlowService


def _registry(path: Path, workspaces: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schema_version": 1, "workspaces": workspaces}, sort_keys=False), encoding="utf-8")
    return path


def _service(tmp_path: Path, workspaces: list[dict[str, object]]) -> WorkspaceFlowService:
    registry = _registry(tmp_path / "workspace_registry.yaml", workspaces)
    return WorkspaceFlowService(
        data_root=tmp_path / "flows",
        matrix=WorkspacePermissionMatrixService(registry).load(),
        approvals=ApprovalService(store=ApprovalStore(root=tmp_path / "approvals")),
        staging_root=tmp_path / "staging",
    )


def test_copy_file_between_registered_workspaces_checks_source_and_target_permissions(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    file_path = source / "input.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = _service(
        tmp_path,
        [
            {"workspace_id": "source", "root_path": str(source), "role": "external_inbox"},
            {"workspace_id": "target", "root_path": str(target), "role": "target_mutable"},
        ],
    )

    plan = service.plan(WorkspaceFlowPlanRequest(operation="copy_file", source_path=str(file_path), target_path=str(target / "input.txt")))

    assert plan.source is not None
    assert plan.source.workspace_id == "source"
    assert plan.target is not None
    assert plan.target.workspace_id == "target"
    assert "target_permission_requires_approval:create_file" in plan.reason_codes


def test_structured_source_target_payload_resolves_workspace_relative_paths(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "input.txt").write_text("hello", encoding="utf-8")
    service = _service(
        tmp_path,
        [
            {"workspace_id": "source", "root_path": str(source), "role": "external_inbox"},
            {"workspace_id": "target", "root_path": str(target), "role": "target_mutable"},
        ],
    )

    plan = service.plan(
        WorkspaceFlowPlanRequest(
            operation="copy_file",
            source=WorkspaceFlowEndpoint(workspace_id="source", path="input.txt"),
            target=WorkspaceFlowEndpoint(workspace_id="target", path="reports/input.txt"),
            requested_by={"type": "user", "id": "test_operator"},
        )
    )

    assert plan.source is not None
    assert plan.source.workspace_id == "source"
    assert plan.source.path == str(source / "input.txt")
    assert plan.target is not None
    assert plan.target.workspace_id == "target"
    assert plan.target.path == str(target / "reports" / "input.txt")
    assert plan.status == "pending_approval"


def test_copy_file_permission_ask_creates_approval(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    file_path = source / "input.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = _service(
        tmp_path,
        [
            {"workspace_id": "source", "root_path": str(source), "role": "external_inbox"},
            {"workspace_id": "target", "root_path": str(target), "role": "target_mutable"},
        ],
    )

    plan = service.plan(WorkspaceFlowPlanRequest(operation="copy_file", source_path=str(file_path), target_path=str(target / "input.txt")))

    assert plan.status == "pending_approval"
    assert plan.approval_id
    approval = service.approvals.get_approval(plan.approval_id)
    assert approval is not None
    assert approval.preview["source_paths"] == [str(file_path)]


def test_copy_file_permission_denied_blocks(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    file_path = source / "input.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = _service(
        tmp_path,
        [
            {"workspace_id": "source", "root_path": str(source), "role": "external_inbox"},
            {"workspace_id": "target", "root_path": str(target), "role": "source_readonly"},
        ],
    )

    plan = service.plan(WorkspaceFlowPlanRequest(operation="copy_file", source_path=str(file_path), target_path=str(target / "input.txt")))

    assert plan.status == "blocked"
    assert "target_permission_denied:create_file" in plan.reason_codes
    assert not (target / "input.txt").exists()


def test_move_file_is_copy_validate_delete_flow(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    file_path = source / "input.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = _service(
        tmp_path,
        [
            {"workspace_id": "source", "root_path": str(source), "role": "target_mutable"},
            {"workspace_id": "target", "root_path": str(target), "role": "target_mutable"},
        ],
    )

    plan = service.plan(WorkspaceFlowPlanRequest(operation="move_file", source_path=str(file_path), target_path=str(target / "input.txt")))

    assert [step.operation for step in plan.steps] == ["read_file", "copy_file", "validate_file", "delete_file", "validate_source_removed"]


def test_approved_flow_executes_only_approved_steps_and_preserves_copy_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    file_path = source / "input.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = _service(
        tmp_path,
        [
            {"workspace_id": "source", "root_path": str(source), "role": "external_inbox"},
            {"workspace_id": "target", "root_path": str(target), "role": "target_mutable"},
        ],
    )
    plan = service.plan(WorkspaceFlowPlanRequest(operation="copy_file", source_path=str(file_path), target_path=str(target / "input.txt")))
    service.approve_plan(plan.flow_plan_id)

    result = service.execute_plan(plan.flow_plan_id)

    assert result.status == "completed"
    assert (target / "input.txt").read_text(encoding="utf-8") == "hello"
    assert file_path.exists()


def test_move_file_does_not_delete_source_before_destination_validation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    file_path = source / "input.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = _service(
        tmp_path,
        [
            {"workspace_id": "source", "root_path": str(source), "role": "target_mutable"},
            {"workspace_id": "target", "root_path": str(target), "role": "target_mutable"},
        ],
    )
    plan = service.plan(WorkspaceFlowPlanRequest(operation="move_file", source_path=str(file_path), target_path=str(target / "missing" / "input.txt")))
    service.approve_plan(plan.flow_plan_id)

    def fail_validation(_plan):
        raise ValueError("destination_validation_failed")

    service._copy_and_validate = fail_validation  # type: ignore[method-assign]
    result = service.execute_plan(plan.flow_plan_id)

    assert result.status == "failed"
    assert file_path.exists()


def test_git_push_requires_specific_approval_and_preview_contains_command(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    service = _service(
        tmp_path,
        [
            {
                "workspace_id": "repo",
                "root_path": str(repo),
                "role": "target_mutable",
                "permissions": {"git_push": "ask"},
            },
        ],
    )

    plan = service.plan(WorkspaceFlowPlanRequest(operation="git_push", source_path=str(repo), command="git push origin main"))

    assert plan.status == "pending_approval"
    assert plan.approval_id
    approval = service.approvals.get_approval(plan.approval_id)
    assert approval is not None
    assert approval.commands == ["git push origin main"]


def test_network_download_goes_to_staging_before_project_import(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    service = _service(
        tmp_path,
        [
            {
                "workspace_id": "staging",
                "root_path": str(staging),
                "role": "temp_staging",
                "permissions": {"network_download": "ask", "create_file": "ask"},
            },
        ],
    )

    plan = service.plan(
        WorkspaceFlowPlanRequest(operation="download_to_staging", source_path="https://example.invalid/file.txt", metadata={"filename": "file.txt"})
    )

    assert plan.target is not None
    assert plan.target.path == str(staging / "file.txt")
    assert plan.status == "pending_approval"
    assert "target_permission_requires_approval:network_download" in plan.reason_codes


def test_external_unregistered_path_requires_registration_or_blocks(tmp_path: Path) -> None:
    source = tmp_path / "outside"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    file_path = source / "input.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = _service(tmp_path, [{"workspace_id": "target", "root_path": str(target), "role": "target_mutable"}])

    plan = service.plan(WorkspaceFlowPlanRequest(operation="copy_file", source_path=str(file_path), target_path=str(target / "input.txt")))

    assert plan.status == "blocked"
    assert "source_workspace_not_registered" in plan.reason_codes


def test_flow_events_include_source_target_and_approval(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    file_path = source / "input.txt"
    file_path.write_text("hello", encoding="utf-8")
    service = _service(
        tmp_path,
        [
            {"workspace_id": "source", "root_path": str(source), "role": "external_inbox"},
            {"workspace_id": "target", "root_path": str(target), "role": "target_mutable"},
        ],
    )
    plan = service.plan(WorkspaceFlowPlanRequest(operation="copy_file", source_path=str(file_path), target_path=str(target / "input.txt")))

    events = (tmp_path / "flows" / "events.jsonl").read_text(encoding="utf-8")

    assert plan.approval_id
    assert plan.flow_plan_id in events
    assert "source" in events
    assert "target" in events
    assert plan.approval_id in events

