from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.models.capability_router_service import CapabilityRouterService

router = APIRouter(prefix="/api/v1/project-analysis", tags=["project-analysis"])


class ProjectAnalysisOperationRequest(BaseModel):
    workspace_ref: str
    objective: str = "general_project_analysis"
    source_channel: str = "api"
    readonly: bool = True
    allow_index: bool = True
    allow_patch_preview: bool = False
    allow_write: bool = False
    allow_shell: bool = False
    allow_build: bool = False
    user_constraints: list[str] = Field(default_factory=list)
    max_files: int = 40
    max_total_bytes: int = 700000


def _policy(workspace_ref: str) -> dict[str, Any]:
    matrix = WorkspacePermissionMatrixService().load()
    read = matrix.decide(path=workspace_ref, permission="read_file")
    listing = matrix.decide(path=workspace_ref, permission="list_files")
    return {"read_file": read.model_dump(), "list_files": listing.model_dump()}


@router.post("/preview")
def preview_project_analysis(request: ProjectAnalysisOperationRequest) -> dict[str, Any]:
    policy = _policy(request.workspace_ref)
    route = CapabilityRouterService().route_preview(operation_type="project_analysis", source_channel=request.source_channel)
    denied = [item for item in policy.values() if item["status"] == "denied"]
    asks = [item for item in policy.values() if item["status"] == "approval_required"]
    status = "blocked" if denied else ("pending_approval" if asks else "previewed")
    return {
        "status": status,
        "operation_id": f"project_analysis_{uuid4().hex}",
        "readonly": request.readonly,
        "write_enabled": False,
        "shell_enabled": False,
        "build_enabled": False,
        "policy_decision": policy,
        "route_decision": route["route_decision"],
        "warnings": ["readonly_request_blocks_write_shell"] if request.readonly else [],
    }


@router.post("/start")
def start_project_analysis(request: ProjectAnalysisOperationRequest) -> dict[str, Any]:
    preview = preview_project_analysis(request)
    if preview["status"] != "previewed":
        return preview
    analysis = ProjectAnalysisService().analyze_project(
        ProjectAnalysisRequest(
            workspace=request.workspace_ref,
            prompt=request.objective,
            goal=request.objective,
            max_files=request.max_files,
            max_total_bytes=request.max_total_bytes,
            include_trace=True,
        )
    )
    search = CapabilityRouterService().workspace_search(query=request.objective, workspace_path=request.workspace_ref, limit=10)
    return {
        "status": analysis.status,
        "operation_id": preview["operation_id"],
        "readonly": True,
        "write_enabled": False,
        "shell_enabled": False,
        "analysis": analysis.model_dump(),
        "workspace_search": search,
        "speaker_truth_status": "no_write_no_shell_claimed",
        "route_decision": preview["route_decision"],
    }
