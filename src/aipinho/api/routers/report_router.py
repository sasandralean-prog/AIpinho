from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.reports.report_artifact import ReportArtifactPreviewRequest
from aipinho.schemas.reports.report_request import ProjectReportRequest, ReportFromAnalysisRequest
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator
from aipinho.services.reports.project_report_service import ProjectReportService
from aipinho.services.reports.report_artifact_preview_service import ReportArtifactPreviewService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/status")
def get_reports_status() -> dict[str, object]:
    service = ProjectReportService()
    preview = ReportArtifactPreviewService()
    return {**service.status(), "artifact_preview": preview.status(), "evaluation": ModelResponseEvaluator().status()}


@router.post("/project")
def create_project_report(request: ProjectReportRequest) -> dict[str, object]:
    response = ProjectReportService().generate_report(request)
    return response.model_dump()


@router.post("/project/from-analysis")
def create_project_report_from_analysis(request: ReportFromAnalysisRequest) -> dict[str, object]:
    response = ProjectReportService().generate_from_analysis(request)
    return response.model_dump()


@router.post("/project/preview-artifact")
def preview_project_report_artifact(request: ReportArtifactPreviewRequest) -> dict[str, object]:
    report = ProjectReportService().get_report(request.report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report_not_found")
    preview = ReportArtifactPreviewService().create_preview(report, request)
    return {"status": preview.status, "preview": preview, "write_enabled": False, "safe_to_execute": False}


@router.get("/{report_id}/evidence")
def get_report_evidence(report_id: str) -> dict[str, object]:
    evidence = ProjectReportService().get_evidence(report_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="report_not_found")
    return {"status": "ok", "report_id": report_id, "evidence": evidence, "vectorstore_enabled": False, "memory_persisted": False}


@router.get("/{report_id}")
def get_report(report_id: str) -> dict[str, object]:
    service = ProjectReportService()
    report = service.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report_not_found")
    return {"status": report.status, "report": report, "rendered_markdown": service.get_markdown(report_id)}

