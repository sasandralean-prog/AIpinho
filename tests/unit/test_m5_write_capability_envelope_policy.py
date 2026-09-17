from __future__ import annotations

from pathlib import Path

from aipinho.schemas.governance.lifecycle import CanonicalPermission
from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.services.tools.write_capability_envelope_service import (
    WriteCapabilityEnvelopeService,
)


def _resource(root: Path, role: str, permissions: list[str]) -> MissionResourceScope:
    return MissionResourceScope(
        resource_id=f"resource_{root.name}_{role}",
        resource_type="local_workspace",
        role=role,
        locator=str(root),
        permissions=permissions,
        provenance_refs=["m5_c1_test"],
    )


def test_dynamic_mutable_envelope_is_canonical_ask_without_human_authority(tmp_path: Path) -> None:
    target = tmp_path / "dynamic_target"
    target.mkdir()
    resource = _resource(target, "target_mutable", ["modify_file"])
    service = WriteCapabilityEnvelopeService()

    result = service.create(
        workspace_path=str(target),
        target_path=str(target / "main.py"),
        operation_type="modify_file",
        preview_id="preview_m5_c1",
        local_resources=[resource],
    )

    assert result.allowed is False
    assert result.envelope.status == "approval_required"
    assert result.canonical_policy_decision is not None
    assert result.canonical_policy_decision.permission == CanonicalPermission.ASK
    assert result.canonical_policy_decision.capability == "modify_file"
    assert any(
        item.facet == "resource_permission"
        and item.permission == CanonicalPermission.ASK
        for item in result.canonical_policy_decision.facets
    )


def test_dynamic_mutable_envelope_allows_same_capability_with_human_authority(tmp_path: Path) -> None:
    target = tmp_path / "dynamic_target"
    target.mkdir()
    resource = _resource(target, "target_mutable", ["modify_file"])
    service = WriteCapabilityEnvelopeService()

    result = service.create(
        workspace_path=str(target),
        target_path=str(target / "main.py"),
        operation_type="modify_file",
        preview_id="preview_m5_c1",
        human_authority_effective=True,
        local_resources=[resource],
    )

    assert result.allowed is True
    assert result.envelope.status == "valid"
    assert result.canonical_policy_decision is not None
    assert result.canonical_policy_decision.permission == CanonicalPermission.ALLOWED
    assert any(
        item.facet == "human_authority"
        and item.permission == CanonicalPermission.ALLOWED
        for item in result.canonical_policy_decision.facets
    )


def test_readonly_resource_denies_write_even_with_human_authority(tmp_path: Path) -> None:
    source = tmp_path / "readonly_source"
    source.mkdir()
    resource = _resource(source, "source_readonly", ["read_file", "list_files"])
    service = WriteCapabilityEnvelopeService()

    result = service.create(
        workspace_path=str(source),
        target_path=str(source / "blocked.py"),
        operation_type="modify_file",
        preview_id="preview_m5_c1",
        human_authority_effective=True,
        local_resources=[resource],
    )

    assert result.allowed is False
    assert result.envelope.status == "blocked"
    assert result.canonical_policy_decision is not None
    assert result.canonical_policy_decision.permission == CanonicalPermission.DENIED
    assert any(
        item.permission == CanonicalPermission.DENIED
        and item.facet in {"workspace_role", "resource_permission"}
        for item in result.canonical_policy_decision.facets
    )
