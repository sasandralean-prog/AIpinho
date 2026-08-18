from __future__ import annotations

from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.schemas.reports.project_report import ProjectReport
from aipinho.schemas.reports.recommendation import Recommendation
from aipinho.schemas.reports.report_request import ProjectReportRequest, ReportFromAnalysisRequest
from aipinho.schemas.reports.report_response import ProjectReportResponse
from aipinho.schemas.reports.report_section import ReportSection
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.reports.evidence_extractor import EvidenceExtractor
from aipinho.services.reports.evidence_index_service import EvidenceIndexService
from aipinho.services.reports.finding_rule_engine import FindingRuleEngine
from aipinho.services.reports.recommendation_service import RecommendationService
from aipinho.services.reports.report_composer import ReportComposer
from aipinho.services.reports.report_formatter import ReportFormatter
from aipinho.services.reports.report_trace_service import ReportTraceService
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import load_yaml_file


class ProjectReportService:
    _reports: dict[str, ProjectReport] = {}
    _evidence: dict[str, list[EvidenceCitation]] = {}
    _markdown: dict[str, str] = {}

    def __init__(self, analysis_service: ProjectAnalysisService | None = None, extractor: EvidenceExtractor | None = None, rule_engine: FindingRuleEngine | None = None, recommendations: RecommendationService | None = None, composer: ReportComposer | None = None, formatter: ReportFormatter | None = None) -> None:
        self.analysis_service = analysis_service or ProjectAnalysisService()
        self.extractor = extractor or EvidenceExtractor()
        self.rule_engine = rule_engine or FindingRuleEngine()
        self.recommendations = recommendations or RecommendationService()
        self.composer = composer or ReportComposer()
        self.formatter = formatter or ReportFormatter()
        self.trace = ReportTraceService()
        self.policy = load_yaml_file(PATHS.config_root / "reports" / "project_report_policy.yaml", critical=True, root=PATHS.config_root / "reports")

    def generate_report(self, request: ProjectReportRequest) -> ProjectReportResponse:
        if request.output.save_file:
            request.output.save_file = False
        if not request.workspace and not (request.analysis_id or request.context_bundle_id):
            report = self._degraded_report("", request.goal, ["workspace_required_for_project_report"])
            self._store(report, "")
            return ProjectReportResponse(status=report.status, report=report, rendered_markdown="", warnings=report.warnings, quality_gate_status=(report.quality_gate or {}).get("status") if report.quality_gate else None)
        if not request.workspace:
            report = self._degraded_report("", request.goal, ["analysis_store_not_available_without_workspace"])
            self._store(report, "")
            return ProjectReportResponse(status=report.status, report=report, rendered_markdown="", warnings=report.warnings, quality_gate_status=(report.quality_gate or {}).get("status") if report.quality_gate else None)
        try:
            analysis = self.analysis_service.analyze_project(
                ProjectAnalysisRequest(
                    workspace=request.workspace,
                    goal=request.goal,
                    max_files=min(20, max(1, request.limits.max_findings)),
                    include_trace=request.include_trace,
                )
            )
            evidence = [*self.extractor.extract_from_tree(analysis.tree_summary), *self.extractor.extract_from_file_context(analysis.file_context)]
            index = EvidenceIndexService(evidence)
            findings = self.rule_engine.evaluate_rules(analysis.tree_summary, analysis.file_context, index)
            findings = [self.recommendations.apply_to_finding(finding) for finding in findings[: request.limits.max_findings]]
            recommendations = [self.recommendations.build_for_finding(finding) for finding in findings]
            report = self.composer.compose(request, analysis, findings, recommendations, index.evidence)
            self._apply_quality_gate(report)
            markdown = self.formatter.to_markdown(report, max_chars=request.limits.max_report_chars)
            self._store(report, markdown)
            return ProjectReportResponse(status=report.status, report=report, rendered_markdown=markdown, warnings=report.warnings, quality_gate_status=(report.quality_gate or {}).get("status") if report.quality_gate else None)
        except Exception as exc:
            report = self._degraded_report(request.workspace, request.goal, ["project_report_dependency_failed", str(exc)])
            self._store(report, "")
            return ProjectReportResponse(status=report.status, report=report, rendered_markdown="", warnings=report.warnings, quality_gate_status=(report.quality_gate or {}).get("status") if report.quality_gate else None)

    def generate_from_analysis(self, request: ReportFromAnalysisRequest) -> ProjectReportResponse:
        if request.workspace:
            return self.generate_report(ProjectReportRequest(workspace=request.workspace, goal=request.goal, include_trace=request.include_trace, analysis_id=request.analysis_id))
        report = self._degraded_report("", request.goal, ["analysis_id_lookup_not_available", request.analysis_id])
        self._store(report, "")
        return ProjectReportResponse(status=report.status, report=report, rendered_markdown="", warnings=report.warnings, quality_gate_status=(report.quality_gate or {}).get("status") if report.quality_gate else None)

    def get_report(self, report_id: str) -> ProjectReport | None:
        return self._reports.get(report_id)

    def get_markdown(self, report_id: str) -> str | None:
        return self._markdown.get(report_id)

    def get_evidence(self, report_id: str) -> list[EvidenceCitation] | None:
        return self._evidence.get(report_id)


    def _apply_quality_gate(self, report: ProjectReport) -> None:
        try:
            from aipinho.services.validation.report_quality_gate_service import ReportQualityGateService
            gate = ReportQualityGateService().validate_report(report, target_id=report.report_id)
            report.quality_gate = gate.summary()
            if gate.status in {"failed", "rejected", "degraded", "needs_review"}:
                report.warnings = list(dict.fromkeys([*report.warnings, f"quality_gate:{gate.status}"]))
                if report.status == "completed":
                    report.status = "degraded"
        except Exception as exc:
            report.quality_gate = {"status": "degraded", "score": 0.0, "safe_to_display": True, "warnings": ["quality_gate_dependency_failed", str(exc)[:500]], "blocking_findings": []}
            report.warnings = list(dict.fromkeys([*report.warnings, "quality_gate_dependency_failed"]))
            if report.status == "completed":
                report.status = "degraded"
    def _store(self, report: ProjectReport, markdown: str) -> None:
        self._reports[report.report_id] = report
        self._evidence[report.report_id] = list(report.evidence_index)
        self._markdown[report.report_id] = markdown

    def _degraded_report(self, workspace: str, goal: str, warnings: list[str]) -> ProjectReport:
        return ProjectReport(
            report_id=f"project_report_{uuid4().hex}",
            workspace=workspace,
            goal=goal,
            status="degraded",
            generated_at=utc_now(),
            executive_summary="Project report could not be generated with sufficient read-only context.",
            sections=[ReportSection(section_id="limitations", title="Limitations", items=[{"limitation": item} for item in warnings])],
            limitations=list(warnings),
            warnings=list(warnings),
            trace=[self.trace.item("project_report_service", "degraded", "report_generation_degraded", source="project_report_service")],
        )

    def status(self) -> dict[str, object]:
        configs = [
            "project_report_policy.yaml",
            "finding_rules.yaml",
            "severity_policy.yaml",
            "report_templates.yaml",
            "evidence_policy.yaml",
            "citation_policy.yaml",
            "recommendation_policy.yaml",
        ]
        return {
            "status": "ok",
            "service": "project_report",
            "deterministic_reports_enabled": True,
            "write_report_enabled": False,
            "artifact_preview_enabled": True,
            "write_enabled": False,
            "patch_enabled": False,
            "shell_enabled": False,
            "git_write_enabled": False,
            "memory_write_enabled": False,
            "rag_enabled": False,
            "llm_required": False,
            "stored_reports": len(self._reports),
            "configs": configs,
            "rule_engine": self.rule_engine.status(),
            "evaluation": ModelResponseEvaluator().status(),
            "model_enhanced_reports_enabled": False,
            "report_quality_gate_enabled": True,
        }



