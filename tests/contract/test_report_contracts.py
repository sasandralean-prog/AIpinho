import pytest
from pydantic import ValidationError

from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.schemas.reports.evidence_finding import EvidenceFinding
from aipinho.schemas.reports.project_report import ProjectReport
from aipinho.schemas.reports.report_artifact import ReportArtifactPreview
from aipinho.schemas.reports.report_request import ProjectReportRequest


def test_report_contracts_forbid_extra_fields_and_validate_nested_models():
    with pytest.raises(ValidationError):
        ProjectReportRequest(workspace="w", extra_field=True)  # type: ignore[call-arg]
    evidence = EvidenceCitation(evidence_id="e", source_type="file", path="a.py", confidence=0.8)
    finding = EvidenceFinding(finding_id="f", title="t", category="architecture", severity="info", summary="s", evidence=[evidence])
    report = ProjectReport(report_id="r", workspace="w", goal="general", status="completed", generated_at="now", executive_summary="s", findings=[finding], evidence_index=[evidence])
    preview = ReportArtifactPreview(preview_id="p", report_id="r", status="preview_ready", target_path="reports/a.md", content_preview="x")
    assert report.findings[0].evidence[0].path == "a.py"
    assert preview.requires_approval is True
