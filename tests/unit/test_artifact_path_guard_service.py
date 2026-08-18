from artifact_fixtures import artifact_workspace
from aipinho.services.artifacts.artifact_path_guard_service import ArtifactPathGuardService


def test_artifact_path_guard_blocks_unsafe_targets(tmp_path):
    workspace = artifact_workspace(tmp_path)
    service = ArtifactPathGuardService()
    assert service.validate(str(workspace), "reports/analysis.md").valid is True
    assert service.validate(str(workspace), "src/app.py").source_code_target is True
    assert service.validate(str(workspace), "config/policies/x.yaml").config_mutation_target is True
    assert service.validate(str(workspace), "reports/../../src/hack.md").path_traversal is True
    outside_allowed_root = tmp_path / "outside_allowed_root"
    outside_allowed_root.mkdir()
    outside = service.validate(str(outside_allowed_root), "reports/a.md")
    assert outside.valid is False
    assert "workspace_root_not_allowed" in outside.blocked_reasons
