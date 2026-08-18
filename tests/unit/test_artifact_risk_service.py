from artifact_fixtures import artifact_workspace
from aipinho.services.artifacts.artifact_content_validator import ArtifactContentValidator
from aipinho.services.artifacts.artifact_path_guard_service import ArtifactPathGuardService
from aipinho.services.artifacts.artifact_risk_service import ArtifactRiskService


def test_artifact_risk_service_levels(tmp_path):
    workspace = artifact_workspace(tmp_path)
    path_guard = ArtifactPathGuardService()
    content = ArtifactContentValidator()
    risk = ArtifactRiskService()
    assert risk.assess(path_guard.validate(str(workspace), "reports/new.md"), content.validate("ok")).risk_level == "low"
    (workspace / "reports" / "existing.md").write_text("old", encoding="utf-8")
    assert risk.assess(path_guard.validate(str(workspace), "reports/existing.md"), content.validate("ok")).risk_level == "medium"
    assert risk.assess(path_guard.validate(str(workspace), "src/app.py"), content.validate("ok")).risk_level == "critical"
    assert risk.assess(path_guard.validate(str(workspace), "reports/a.md"), content.validate("api_key=abc123")).risk_level == "critical"
