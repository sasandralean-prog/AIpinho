from aipinho.schemas.analysis.analysis_report import AnalysisReport
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_analysis_result import ProjectAnalysisResult
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.schemas.reports.evidence_finding import EvidenceFinding
from aipinho.schemas.reports.report_request import ProjectReportRequest
from aipinho.services.reports.report_composer import ReportComposer
from aipinho.services.reports.report_formatter import ReportFormatter


def test_report_composer_and_formatter_include_sections_findings_evidence_limitations():
    evidence = EvidenceCitation(evidence_id="e1", source_type="file", path="src/a.py", line_start=1, line_end=1, excerpt="x", confidence=0.8)
    finding = EvidenceFinding(finding_id="f1", title="Finding", category="architecture", severity="info", confidence=0.8, summary="s", evidence=[evidence], inference="i", recommendation="r")
    analysis = ProjectAnalysisResult(result_id="a", workspace="w", status="partial", tree_summary=ProjectTreeSummary(workspace="w", status="ok", candidate_files=["src/a.py"]), file_context=FileContextBundle(bundle_id="b", workspace="w", status="partial"), report=AnalysisReport(report_id="ar", status="partial", title="t", summary="s", limitations=["limited"]))

    report = ReportComposer().compose(ProjectReportRequest(workspace="w"), analysis, [finding], [], [evidence])
    markdown = ReportFormatter().to_markdown(report)

    assert report.sections
    assert "Evidence-Based Findings" in markdown
    assert "src/a.py" in markdown
    assert "limited" in markdown
