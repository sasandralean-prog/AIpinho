from pathlib import Path

from artifact_fixtures import artifact_service, artifact_workspace, preview_request


def test_artifact_writer_preview_service_valid_blocked_and_no_write(tmp_path):
    workspace = artifact_workspace(tmp_path)
    service = artifact_service(tmp_path)
    preview = service.create_preview(preview_request(workspace))
    assert preview.status == "needs_approval"
    assert preview.write_allowed_now is False
    assert preview.safe_to_execute is False
    assert not Path(workspace / "reports" / "analysis.md").exists()
    blocked = service.create_preview(preview_request(workspace, target_path="src/app.py"))
    assert blocked.status == "blocked"
    assert "source_code_target" in blocked.blocked_reasons
    secret = service.create_preview(preview_request(workspace, content="api_key=abc123"))
    assert secret.status == "blocked"
    assert secret.risk.risk_level == "critical"
