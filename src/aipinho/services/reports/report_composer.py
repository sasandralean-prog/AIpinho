from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.analysis.project_analysis_result import ProjectAnalysisResult
from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.schemas.reports.evidence_finding import EvidenceFinding
from aipinho.schemas.reports.project_report import ProjectReport
from aipinho.schemas.reports.recommendation import Recommendation
from aipinho.schemas.reports.report_request import ProjectReportRequest
from aipinho.schemas.reports.report_section import ReportSection
from aipinho.services.reports.report_trace_service import ReportTraceService
from aipinho.services.prompt_intelligence.report_deliverable_extractor_service import (
    ReportDeliverableExtractorService,
)
from aipinho.services.reports.project_portability_plan_service import (
    ProjectPortabilityPlanService,
)
from aipinho.services.session.session_store import utc_now


class ReportComposer:
    def __init__(self) -> None:
        self.trace = ReportTraceService()
        self.deliverables = ReportDeliverableExtractorService()
        self.portability = ProjectPortabilityPlanService()

    def compose(self, request: ProjectReportRequest, analysis: ProjectAnalysisResult, findings: list[EvidenceFinding], recommendations: list[Recommendation], evidence_index: list[EvidenceCitation]) -> ProjectReport:
        status = self._status(analysis, findings)
        limitations = list(dict.fromkeys([*analysis.report.limitations, *analysis.warnings]))
        if analysis.file_context.omitted_files:
            limitations.append("file_context_omitted_files_present")
        if not findings:
            limitations.append("no_evidence_cited_findings_emitted")
        executive = self._executive_summary(analysis, findings)
        sections = self._sections(analysis, findings)
        planning = self.portability.build(
            analysis=analysis,
            recommendations=recommendations,
            workspace_references=request.workspace_references,
        )
        requested = list(dict.fromkeys(request.requested_deliverables))
        additional, fulfilled = self._requested_sections(
            requested,
            analysis=analysis,
            findings=findings,
            recommendations=recommendations,
            evidence_index=evidence_index,
            planning=planning,
        )
        sections.extend(additional)
        missing = [item for item in requested if item not in fulfilled]
        if missing:
            status = "partial"
            limitations.append(
                "missing_requested_deliverables:" + ",".join(missing)
            )
        return ProjectReport(
            report_id=f"project_report_{uuid4().hex}",
            workspace=analysis.workspace,
            goal=request.goal,
            status=status,
            generated_at=utc_now(),
            source_analysis_id=analysis.result_id,
            source_context_bundle_id=analysis.file_context.bundle_id,
            executive_summary=executive,
            sections=sections,
            findings=findings,
            recommendations=recommendations,
            limitations=list(dict.fromkeys(limitations)),
            evidence_index=evidence_index,
            warnings=list(dict.fromkeys([*analysis.warnings, *( ["save_file_disabled_use_artifact_preview"] if request.output.save_file else [] )])),
            trace=[self.trace.item("report_composer", status, "project_report_composed", source="report_composer", data={"findings": len(findings), "evidence": len(evidence_index)})],
            requested_deliverables=requested,
            fulfilled_deliverables=fulfilled,
            missing_deliverables=missing,
        )

    def _status(self, analysis: ProjectAnalysisResult, findings: list[EvidenceFinding]) -> str:
        if analysis.status == "blocked":
            return "blocked"
        if analysis.status in {"degraded", "invalid"}:
            return "degraded"
        if analysis.status == "ok" and findings and analysis.file_context.status == "ok":
            return "completed"
        return "partial"

    def _executive_summary(self, analysis: ProjectAnalysisResult, findings: list[EvidenceFinding]) -> str:
        return (
            f"{analysis.report.summary} "
            f"The evidence report used {len(analysis.file_context.items)} context files, "
            f"{len(analysis.tree_summary.candidate_files)} candidate paths and {len(findings)} policy findings. "
            "No write, patch, shell, git, memory, RAG/vectorstore or mandatory LLM action was executed."
        )

    def _sections(self, analysis: ProjectAnalysisResult, findings: list[EvidenceFinding]) -> list[ReportSection]:
        return [
            ReportSection(section_id="executive_summary", title="Executive Summary", content=self._executive_summary(analysis, findings)),
            ReportSection(section_id="project_structure", title="Project Structure", items=[{"structure": item} for item in analysis.structures]),
            ReportSection(
                section_id="observed_functionality",
                title="Observed Functionality",
                items=[
                    {
                        "title": item.title,
                        "summary": item.summary,
                        "evidence_paths": item.evidence_paths,
                    }
                    for item in analysis.findings
                    if item.category == "functionality"
                ],
            ),
            ReportSection(
                section_id="analysis_findings",
                title="Analysis Findings",
                items=[
                    {
                        "category": item.category,
                        "severity": item.severity,
                        "title": item.title,
                        "summary": item.summary,
                        "evidence_paths": item.evidence_paths,
                    }
                    for item in analysis.findings
                    if item.category != "functionality"
                ],
            ),
            ReportSection(section_id="findings", title="Evidence-Based Findings", items=[finding.model_dump() for finding in findings]),
            ReportSection(section_id="limitations", title="Scope and Limitations", items=[{"limitation": item} for item in analysis.report.limitations]),
        ]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "report_composer"}

    def _requested_sections(
        self,
        requested: list[str],
        *,
        analysis,
        findings,
        recommendations,
        evidence_index,
        planning: dict[str, object],
    ) -> tuple[list[ReportSection], list[str]]:
        definitions = self.deliverables.definitions()
        sections: list[ReportSection] = []
        fulfilled: list[str] = []
        for deliverable_id in requested:
            definition = definitions.get(deliverable_id)
            if not definition:
                continue
            items = self._strategy_items(
                str(definition.get("strategy") or ""),
                analysis=analysis,
                findings=findings,
                recommendations=recommendations,
                evidence_index=evidence_index,
                planning=planning,
            )
            if not items:
                continue
            sections.append(
                ReportSection(
                    section_id=deliverable_id,
                    title=str(definition.get("title") or deliverable_id),
                    items=items,
                )
            )
            fulfilled.append(deliverable_id)
        return sections, fulfilled

    def _strategy_items(
        self,
        strategy: str,
        *,
        analysis,
        findings,
        recommendations,
        evidence_index,
        planning: dict[str, object],
    ) -> list[dict[str, object]]:
        if strategy == "diagnosis":
            return [
                {
                    "title": item.title,
                    "summary": item.summary,
                    "evidence_paths": item.evidence_paths,
                }
                for item in analysis.findings
            ]
        if strategy == "project_overview":
            return [
                {"title": "Structure", "summary": ", ".join(analysis.structures)},
                {
                    "title": "Scope",
                    "summary": analysis.report.summary,
                },
            ]
        if strategy == "target_workspace_status":
            target = planning.get("target_status", {})
            if not isinstance(target, dict):
                return []
            return [
                {
                    "title": "Target workspace",
                    "summary": (
                        f"Status: {target.get('status')}; files seen: {target.get('files_seen')}; "
                        f"directories seen: {target.get('dirs_seen')}."
                    ),
                    "details": {
                        "path": target.get("path"),
                        "top_level": target.get("top_level", []),
                        "warnings": target.get("warnings", []),
                        "violations": target.get("violations", []),
                    },
                }
            ]
        if strategy == "problems":
            return [
                {
                    "title": item.title,
                    "summary": item.summary,
                    "severity": item.severity,
                }
                for item in findings
            ] or [
                {
                    "title": item.title,
                    "summary": item.summary,
                    "severity": item.severity,
                }
                for item in analysis.findings
                if item.category != "functionality"
            ]
        if strategy == "opportunities":
            return [
                {"title": "Recommendation", "summary": item.summary}
                for item in recommendations
            ]
        if strategy == "macro_plan":
            return [
                {
                    "title": str(item.get("title") or item.get("stage_id")),
                    "summary": str(item.get("objective") or ""),
                    "details": {"validation": item.get("validation", [])},
                }
                for item in planning.get("macro_plan", []) or []
                if isinstance(item, dict)
            ]
        if strategy == "first_sprint":
            first = planning.get("first_sprint", {})
            if not isinstance(first, dict):
                return []
            return [
                {
                    "title": "Sprint 1",
                    "summary": str(first.get("objective") or ""),
                    "details": {
                        "scope": first.get("scope"),
                        "excluded": first.get("excluded"),
                    },
                }
            ]
        if strategy == "risks":
            return [
                {
                    "title": str(item.get("risk") or "Risk"),
                    "summary": str(item.get("summary") or ""),
                }
                for item in planning.get("risks", []) or []
                if isinstance(item, dict)
            ]
        if strategy == "permissions":
            return [
                {"title": "Permission", "summary": str(item)}
                for item in planning.get("permissions", []) or []
            ]
        if strategy == "next_steps":
            return [
                {"title": "Next step", "summary": str(item)}
                for item in planning.get("next_steps", []) or []
            ]
        if strategy == "evidence":
            return [
                {
                    "title": item.path or item.source_type,
                    "summary": item.excerpt or item.source_type,
                }
                for item in evidence_index
            ]
        if strategy == "validation_strategy":
            return [
                {"title": "Validation", "summary": str(item)}
                for item in planning.get("validation_strategy", []) or []
            ]
        return []
