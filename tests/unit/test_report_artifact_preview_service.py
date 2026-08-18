from aipinho.schemas.reports.report_artifact import ReportArtifactPreviewRequest
from aipinho.schemas.reports.report_request import ProjectReportRequest
from aipinho.services.reports.project_report_service import ProjectReportService
from aipinho.services.reports.report_artifact_preview_service import ReportArtifactPreviewService


def test_report_artifact_preview_requires_approval_and_does_not_write(tmp_path):
    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    response = ProjectReportService().generate_report(ProjectReportRequest(workspace=str(tmp_path)))
    target = tmp_path / "reports" / "analysis.md"

    preview = ReportArtifactPreviewService().create_preview(response.report, ReportArtifactPreviewRequest(report_id=response.report.report_id, workspace=str(tmp_path), target_path="reports/analysis.md"))

    assert preview.status == "preview_ready"
    assert preview.would_write is True
    assert preview.requires_approval is True
    assert preview.safe_to_execute is False
    assert not target.exists()


def test_report_artifact_preview_blocks_forbidden_target(tmp_path):
    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    response = ProjectReportService().generate_report(ProjectReportRequest(workspace=str(tmp_path)))
    preview = ReportArtifactPreviewService().create_preview(response.report, ReportArtifactPreviewRequest(report_id=response.report.report_id, workspace=str(tmp_path), target_path="C:\\PinhoabacaxiAI\\report.md"))
    assert preview.status == "blocked"
    assert preview.safe_to_execute is False
    assert preview.violations
