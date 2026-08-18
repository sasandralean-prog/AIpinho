from __future__ import annotations

from aipinho.schemas.skills.contracts import SkillManifest
from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService, SkillManifestValidatorV2


def test_registry_seeds_internal_skill_manifests(tmp_path):
    registry = SkillManifestRegistryService(root=tmp_path / "registry")

    status = registry.status()

    assert status.manifest_count >= 5
    assert status.active_count >= 4
    assert status.invalid_count == 0
    assert "internal.safe_markdown_report_generator" in {item.skill_id for item in registry.list_manifests()}


def test_mobile_skill_view_is_sanitized_and_readonly(tmp_path):
    registry = SkillManifestRegistryService(root=tmp_path / "registry")

    view = registry.mobile_view()

    assert view["state"]["raw_default_visible"] is False
    assert view["skills"]
    assert "allowed_tools" not in view["skills"][0]


def test_manifest_with_fake_secret_like_value_is_rejected():
    manifest = SkillManifest(
        skill_id="internal.bad_secret_skill",
        display_name="Bad Secret Skill",
        slug="bad_secret_skill",
        description="Should not be accepted.",
        version="1.0.0",
        status="active",
        category="analysis",
        compatible_agents=["aipinho"],
        required_capabilities=["read_workspace"],
        allowed_tools=["list_dir"],
        denied_tools=[],
        workspace_policy={"source_readonly_write": False},
        artifact_policy={"requires_token": True},
        memory_policy={"mode": "none"},
        validation_policy={"required": False},
        speaker_truth_policy={"raw_hidden_by_default": True},
        metadata_sanitized={"fake_api_key": "sk-test-000000000000000000000000"},
    )

    result = SkillManifestValidatorV2().validate(manifest)

    assert result.valid is False
    assert "secret_detected" in result.reason_codes


def test_manifest_cannot_write_source_readonly():
    manifest = SkillManifest(
        skill_id="internal.bad_workspace_skill",
        display_name="Bad Workspace Skill",
        slug="bad_workspace_skill",
        description="Should not write source_readonly.",
        version="1.0.0",
        status="active",
        category="analysis",
        compatible_agents=["aipinho"],
        required_capabilities=["workspace_write"],
        allowed_tools=["create_file"],
        denied_tools=[],
        workspace_policy={"source_readonly_write": True},
        artifact_policy={"requires_token": True},
        memory_policy={"mode": "none"},
        validation_policy={"required": False},
        speaker_truth_policy={"raw_hidden_by_default": True},
        risk_level="medium",
        approval_policy={"required": True},
    )

    result = SkillManifestValidatorV2().validate(manifest)

    assert result.valid is False
    assert "source_readonly_write_declared" in result.reason_codes
