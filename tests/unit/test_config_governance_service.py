from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aipinho.schemas.config_governance.config_change import ConfigChangeRequest
from aipinho.schemas.config_governance.workspace_permission import WorkspaceEntry
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.config_governance.config_governance_service import ConfigGovernanceService


def _write_targets(config_root: Path) -> None:
    targets = {
        ("workspaces", "workspace_registry.yaml"): {"schema_version": 1, "workspaces": []},
        ("artifacts", "artifact_write_policy.yaml"): {"schema_version": 1, "artifact": {"enabled": True}},
        ("policies", "patch_policy.yaml"): {"schema_version": 1, "patch": {"enabled": True}},
        ("policies", "governed_tool_execution_policy.yaml"): {"schema_version": 1, "tools": {"enabled": True}},
        ("models", "local_provider_policy.yaml"): {"schema_version": 1, "providers": {}},
        ("agents", "agent_registry.yaml"): {"schema_version": 1, "agents": []},
    }
    for parts, payload in targets.items():
        path = config_root.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _service(tmp_path: Path) -> ConfigGovernanceService:
    config_root = tmp_path / "config"
    _write_targets(config_root)
    return ConfigGovernanceService(
        config_root=config_root,
        data_root=tmp_path / "runtime" / "config_governance",
        approvals=ApprovalService(store=ApprovalStore(root=tmp_path / "approvals")),
    )


def test_config_change_create_returns_change_id(tmp_path: Path) -> None:
    service = _service(tmp_path)
    change = service.create_change(ConfigChangeRequest(target="workspace_registry", operation="merge", payload={"defaults": {"sample": True}}))

    assert change.change_id.startswith("config_change_")
    assert change.status == "draft"


def test_config_change_preview_generates_diff_and_requires_approval(tmp_path: Path) -> None:
    service = _service(tmp_path)
    change = service.create_change(ConfigChangeRequest(target="workspace_registry", operation="merge", payload={"defaults": {"sample": True}}))

    preview = service.preview_change(change.change_id)

    assert preview.validation_status == "ok"
    assert preview.requires_approval is True
    assert preview.approval_id
    assert "sample: true" in preview.sanitized_diff.lower()


def test_config_change_preview_sanitizes_secrets(tmp_path: Path) -> None:
    service = _service(tmp_path)
    change = service.create_change(
        ConfigChangeRequest(target="provider_policy", operation="merge", payload={"providers": {"x": {"api_key": "sk-testsecret123456"}}})
    )

    preview = service.preview_change(change.change_id)

    assert "sk-testsecret" not in preview.sanitized_diff
    assert "[REDACTED]" in preview.sanitized_diff


def test_config_change_apply_requires_approved_status(tmp_path: Path) -> None:
    service = _service(tmp_path)
    change = service.create_change(ConfigChangeRequest(target="workspace_registry", operation="merge", payload={"defaults": {"sample": True}}))
    service.preview_change(change.change_id)

    with pytest.raises(ValueError, match="config_change_apply_requires_approved_status"):
        service.apply_change(change.change_id)


def test_config_change_apply_creates_backup_reloads_and_self_checks(tmp_path: Path) -> None:
    service = _service(tmp_path)
    change = service.create_change(ConfigChangeRequest(target="workspace_registry", operation="merge", payload={"defaults": {"sample": True}}))
    service.preview_change(change.change_id)
    service.approve_change(change.change_id)

    result = service.apply_change(change.change_id)

    assert result.status == "applied"
    assert result.backup_id
    assert result.reload_status == "ok"
    assert result.self_check_status == "ok"
    assert service.get_backup(result.backup_id) is not None


def test_invalid_config_change_is_rejected_without_file_write(tmp_path: Path) -> None:
    service = _service(tmp_path)
    registry_path = service.target_path("workspace_registry")
    before = registry_path.read_text(encoding="utf-8")
    entry = {
        "workspace_id": "bad",
        "root_path": "relative/path",
        "role": "target_mutable",
    }

    change = service.create_change(ConfigChangeRequest(target="workspace_registry", operation="add_workspace", payload={"workspace": entry}))
    preview = service.preview_change(change.change_id)

    assert preview.validation_status == "failed"
    assert registry_path.read_text(encoding="utf-8") == before


def test_rollback_restores_previous_config(tmp_path: Path) -> None:
    service = _service(tmp_path)
    registry_path = service.target_path("workspace_registry")
    before = registry_path.read_text(encoding="utf-8")
    change = service.create_change(ConfigChangeRequest(target="workspace_registry", operation="merge", payload={"defaults": {"sample": True}}))
    service.preview_change(change.change_id)
    service.approve_change(change.change_id)
    applied = service.apply_change(change.change_id)

    service.rollback(applied.backup_id or "")

    assert registry_path.read_text(encoding="utf-8") == before


def test_effective_policy_reflects_applied_workspace_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    entry = WorkspaceEntry(workspace_id="sample", root_path=str(tmp_path / "sample"), role="target_mutable")
    change = service.create_change(
        ConfigChangeRequest(target="workspace_registry", operation="add_workspace", payload={"workspace": entry.model_dump()})
    )
    service.preview_change(change.change_id)
    service.approve_change(change.change_id)
    service.apply_change(change.change_id)

    effective = service.effective_policy()

    workspaces = effective["workspace_permission_matrix"]["workspaces"]  # type: ignore[index]
    assert any(item["workspace_id"] == "sample" for item in workspaces)


def test_missing_optional_provider_does_not_break_config_health(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.target_path("provider_policy").unlink()

    health = service.health()

    assert health["targets"]["provider_policy"]["status"] == "ok"  # type: ignore[index]


def test_openai_disabled_is_not_system_error(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.target_path("provider_policy").write_text(
        yaml.safe_dump({"schema_version": 1, "providers": {"openai": {"enabled": False}}}, sort_keys=False),
        encoding="utf-8",
    )

    health = service.health()

    assert health["status"] == "ok"
    assert health["targets"]["provider_policy"]["status"] == "ok"  # type: ignore[index]


def test_config_apply_failure_does_not_leave_partial_invalid_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(tmp_path)
    registry_path = service.target_path("workspace_registry")
    before = registry_path.read_text(encoding="utf-8")
    change = service.create_change(ConfigChangeRequest(target="workspace_registry", operation="merge", payload={"defaults": {"sample": True}}))
    service.preview_change(change.change_id)
    service.approve_change(change.change_id)

    def fail_reload() -> dict[str, object]:
        raise ValueError("synthetic_reload_failure")

    monkeypatch.setattr(service, "reload", fail_reload)
    result = service.apply_change(change.change_id)

    assert result.status == "failed"
    assert "synthetic_reload_failure" in result.errors
    assert registry_path.read_text(encoding="utf-8") == before


def test_config_change_events_are_emitted(tmp_path: Path) -> None:
    service = _service(tmp_path)
    change = service.create_change(ConfigChangeRequest(target="workspace_registry", operation="merge", payload={"defaults": {"sample": True}}))
    preview = service.preview_change(change.change_id)

    updated = service.get_change(change.change_id)

    assert preview.approval_id
    assert updated is not None
    event_types = {event["event_type"] for event in updated.events}
    assert "config_change_created" in event_types
    assert "config_change_preview_created" in event_types
    assert "config_change_approval_required" in event_types
