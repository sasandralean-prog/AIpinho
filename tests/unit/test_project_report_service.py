from aipinho.schemas.reports.report_request import ProjectReportRequest
from aipinho.services.reports.project_report_service import ProjectReportService


def test_project_report_service_generates_evidence_report_without_write(tmp_path):
    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "policies").mkdir()
    (tmp_path / "config" / "policies" / "x.yaml").write_text("schema_version: 1", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("from fastapi import FastAPI", encoding="utf-8")

    response = ProjectReportService().generate_report(ProjectReportRequest(workspace=str(tmp_path), goal="architecture_overview"))

    assert response.write_enabled is False
    assert response.report is not None
    assert response.report.status in {"completed", "partial"}
    assert response.report.findings
    assert all(finding.evidence for finding in response.report.findings)


def test_project_report_service_blocks_forbidden_root():
    response = ProjectReportService().generate_report(ProjectReportRequest(workspace=r"C:\PinhoabacaxiAI", goal="security_readonly"))
    assert response.report is not None
    assert response.report.status in {"blocked", "partial", "degraded"}
    assert response.write_enabled is False
