from __future__ import annotations

import json
from typing import Any

from aipinho.schemas.artifacts.artifact_source import ArtifactResolvedSource, ArtifactSource
from aipinho.services.reports.project_report_service import ProjectReportService
from aipinho.services.reports.report_formatter import ReportFormatter
from aipinho.services.roles.role_pipeline_service import RolePipelineService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.validation.validation_gate_service import ValidationGateService


class ArtifactSourceResolver:
    def __init__(self) -> None:
        self.report_service = ProjectReportService()
        self.task_runtime = TaskRuntimeService()
        self.role_pipeline = RolePipelineService()
        self.validation_gate = ValidationGateService()
        self.report_formatter = ReportFormatter()

    def resolve(self, source: ArtifactSource) -> ArtifactResolvedSource:
        if source.source_type in {"user_provided_content", "deterministic_export"}:
            if source.content is None:
                return self._blocked(source, "source_content_required")
            return ArtifactResolvedSource(source=source, content=source.content, format=source.format, status="resolved")
        if not source.source_id:
            return self._blocked(source, "source_id_required")
        if source.source_type == "project_report":
            report = self.report_service.get_report(source.source_id)
            if report is None:
                return self._blocked(source, "project_report_not_found")
            quality = report.quality_gate or {}
            if quality.get("status") in {"failed", "rejected", "degraded"}:
                return self._blocked(source, "project_report_quality_gate_not_passed", validation_summary=quality)
            content = self.report_formatter.to_markdown(report) if source.format == "markdown" else json.dumps(report.model_dump(), ensure_ascii=False, indent=2)
            return ArtifactResolvedSource(source=source, content=content, format=source.format, validation_summary=quality, warnings=list(report.warnings))
        if source.source_type == "task_run_result":
            try:
                result = self.task_runtime.get_result(source.source_id)
            except ValueError:
                return self._blocked(source, "task_run_result_invalid_id")
            if result is None:
                return self._blocked(source, "task_run_result_not_found")
            validation = result.validation or {}
            if not validation:
                return self._blocked(source, "task_run_result_validation_missing")
            if validation.get("status") in {"failed", "rejected", "degraded"}:
                return self._blocked(source, "task_run_result_validation_not_passed", validation_summary=validation)
            content = self._task_result_markdown(result) if source.format == "markdown" else json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
            return ArtifactResolvedSource(source=source, content=content, format=source.format, validation_summary=validation, warnings=list(result.warnings))
        if source.source_type == "validation_result":
            try:
                result = self.validation_gate.get_result(source.source_id)
            except ValueError:
                return self._blocked(source, "validation_result_invalid_id")
            if result is None:
                return self._blocked(source, "validation_result_not_found")
            content = self._validation_markdown(result) if source.format == "markdown" else json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
            return ArtifactResolvedSource(source=source, content=content, format=source.format, validation_summary=result.summary(), warnings=list(result.warnings))
        if source.source_type == "role_pipeline_run":
            try:
                run = self.role_pipeline.get_run(source.source_id)
            except ValueError:
                return self._blocked(source, "role_pipeline_run_invalid_id")
            if run is None:
                return self._blocked(source, "role_pipeline_run_not_found")
            validation = run.validation_summary or {}
            content = f"# Role Pipeline Run\n\n- run_id: {run.run_id}\n- status: {run.status}\n- validation: {validation.get('status', 'unknown')}\n" if source.format == "markdown" else json.dumps(run.model_dump(), ensure_ascii=False, indent=2)
            return ArtifactResolvedSource(source=source, content=content, format=source.format, validation_summary=validation, warnings=list(run.warnings))
        return self._blocked(source, "unsupported_source_type")

    def _blocked(self, source: ArtifactSource, reason: str, *, validation_summary: dict[str, Any] | None = None) -> ArtifactResolvedSource:
        return ArtifactResolvedSource(source=source, content="", format=source.format, status="blocked", validation_summary=validation_summary or {}, blocked_reasons=[reason])

    def _task_result_markdown(self, result: Any) -> str:
        outputs = result.outputs if isinstance(result.outputs, dict) else {}
        project_report = outputs.get("project_report")
        if isinstance(project_report, dict):
            rendered = project_report.get("rendered_markdown")
            if isinstance(rendered, str) and rendered.strip():
                return rendered.strip() + "\n"
        return (
            f"# Task Run Result\n\n"
            f"- run_id: {result.run_id}\n"
            f"- status: {result.status}\n\n"
            f"## Summary\n\n{result.summary}\n\n"
            f"## Validation\n\n"
            f"{json.dumps(result.validation or {}, ensure_ascii=False, indent=2)}\n"
        )

    def _validation_markdown(self, result: Any) -> str:
        return f"# Validation Result\n\n- validation_id: {result.validation_id}\n- target_type: {result.target_type}\n- status: {result.status}\n- score: {result.score}\n\n## Blocking Findings\n\n{', '.join(result.blocking_findings) or 'none'}\n"

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_source_resolver", "do_not_invent_content": True}
