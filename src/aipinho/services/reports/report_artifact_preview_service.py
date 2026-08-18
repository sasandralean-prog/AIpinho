from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.reports.project_report import ProjectReport
from aipinho.schemas.reports.report_artifact import ReportArtifactPreview, ReportArtifactPreviewRequest
from aipinho.services.reports.report_formatter import ReportFormatter
from aipinho.services.reports.report_trace_service import ReportTraceService
from aipinho.services.security.path_guard_service import PathGuardService


class ReportArtifactPreviewService:
    _previews: dict[str, ReportArtifactPreview] = {}

    def __init__(self, formatter: ReportFormatter | None = None, path_guard: PathGuardService | None = None) -> None:
        self.formatter = formatter or ReportFormatter()
        self.path_guard = path_guard or PathGuardService()
        self.trace = ReportTraceService()

    def create_preview(self, report: ProjectReport, request: ReportArtifactPreviewRequest) -> ReportArtifactPreview:
        workspace = request.workspace or report.workspace
        decision = self.path_guard.validate_read_target(workspace, request.target_path)
        if not decision.allowed:
            preview = ReportArtifactPreview(
                preview_id=f"report_preview_{uuid4().hex}",
                report_id=report.report_id,
                status="blocked",
                target_path=request.target_path,
                content_preview="",
                would_write=True,
                requires_approval=True,
                safe_to_execute=False,
                warnings=list(decision.warnings),
                violations=list(decision.violations),
                trace=[*self.trace_from_raw(decision.trace), self.trace.item("report_artifact_preview", "blocked", decision.reason, source="path_guard")],
            )
            self._previews[preview.preview_id] = preview
            return preview
        content = self.formatter.to_markdown(report) if request.format == "markdown" else report.model_dump_json(indent=2)
        preview = ReportArtifactPreview(
            preview_id=f"report_preview_{uuid4().hex}",
            report_id=report.report_id,
            status="preview_ready",
            target_path=request.target_path,
            content_preview=content,
            would_write=True,
            requires_approval=True,
            safe_to_execute=False,
            trace=[self.trace.item("report_artifact_preview", "preview_ready", "artifact_preview_created_without_write", source="report_artifact_preview_service")],
        )
        self._previews[preview.preview_id] = preview
        return preview

    def get_preview(self, preview_id: str) -> ReportArtifactPreview | None:
        return self._previews.get(preview_id)

    def trace_from_raw(self, raw_items: list[dict]) -> list:
        return [self.trace.item(str(item.get("stage", "path_guard")), str(item.get("decision", item.get("status", "blocked"))), str(item.get("reason", item.get("rule", ""))), source=item.get("source")) for item in raw_items if isinstance(item, dict)]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "report_artifact_preview", "write_enabled": False, "artifact_preview_enabled": True, "stored_previews": len(self._previews)}
