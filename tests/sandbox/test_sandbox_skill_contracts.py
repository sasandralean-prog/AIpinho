from __future__ import annotations

from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService


def test_sandbox_skill_manifests_are_registered() -> None:
    registry = SkillManifestRegistryService()
    expected = {
        "sandbox_file_writer",
        "sandbox_project_generator",
        "sandbox_shell_runner",
        "sandbox_artifact_exporter",
        "sandbox_validation_runner",
    }
    manifests = registry.list_manifests()
    by_name = {manifest.slug: manifest for manifest in manifests}

    assert expected <= by_name.keys()
    for name in expected:
        manifest = by_name[name]
        assert manifest.sandbox_allowed is True
        assert manifest.sandbox_required is True
        assert manifest.allowed_tools
