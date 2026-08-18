from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.analysis.file_selection import FileSelectionRequest
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.services.analysis.analysis_report_service import AnalysisReportService
from aipinho.services.analysis.file_context_builder import FileContextBuilder
from aipinho.services.analysis.file_selection_service import FileSelectionService
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.analysis.project_structure_detector import ProjectStructureDetector
from aipinho.services.analysis.project_tree_service import ProjectTreeService

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/status")
def get_analysis_status() -> dict[str, object]:
    return ProjectAnalysisService().status()


@router.post("/project")
def analyze_project(request: ProjectAnalysisRequest) -> dict[str, object]:
    result = ProjectAnalysisService().analyze_project(request)
    return {"status": result.status, "result": result, "write_enabled": False, "patch_enabled": False, "shell_enabled": False}


@router.post("/project/tree")
def analyze_project_tree(request: ProjectAnalysisRequest) -> dict[str, object]:
    tree = ProjectTreeService().build_tree_summary(request)
    return {"status": tree.status, "tree_summary": tree, "content_read": False}


@router.post("/project/context")
def build_project_context(request: ProjectAnalysisRequest) -> dict[str, object]:
    tree = ProjectTreeService().build_tree_summary(request)
    selection = FileSelectionService().select_files(
        FileSelectionRequest(
            workspace=tree.workspace if tree.status not in {"blocked", "invalid"} else request.workspace,
            goal=request.goal,
            candidate_files=tree.candidate_files,
            focus_paths=request.focus_paths,
            max_files=request.max_files,
            max_total_bytes=request.max_total_bytes,
        )
    )
    bundle = FileContextBuilder().build_context(request, selection)
    return {"status": bundle.status, "context_bundle": bundle, "raw_log_exposed": False}


@router.post("/project/report")
def build_project_report(request: ProjectAnalysisRequest) -> dict[str, object]:
    result = ProjectAnalysisService().analyze_project(request)
    return {"status": result.report.status, "report": result.report, "findings": result.findings}
