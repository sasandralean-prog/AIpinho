from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from aipinho.schemas.projects import (
    ProjectProfileCreateRequest,
    ProjectProfileDetectionRequest,
    ProjectProfileSelectionRequest,
    ProjectProfileUpdateRequest,
)
from aipinho.services.projects import ProjectProfileHealthService, ProjectProfileRegistryService

router = APIRouter(prefix="/api/v1/projects/profiles", tags=["project-profiles"])


@router.get("")
def list_project_profiles() -> dict[str, object]:
    service = ProjectProfileRegistryService()
    return {"status": "ok", "profiles": [item.model_dump() for item in service.list_profiles()]}


@router.get("/status")
def project_profiles_status() -> dict[str, object]:
    return ProjectProfileRegistryService().status()


@router.get("/mobile-selector")
def project_profiles_mobile_selector() -> dict[str, object]:
    return ProjectProfileRegistryService().mobile_selector_view()


@router.get("/doctor/health")
def project_profiles_doctor_health() -> dict[str, object]:
    return ProjectProfileHealthService().status()


@router.post("/detect")
def detect_project_profile(request: ProjectProfileDetectionRequest) -> dict[str, object]:
    return ProjectProfileRegistryService().detect(request.root_path, display_name=request.display_name, create_draft=request.create_draft)


@router.post("")
def create_project_profile(request: ProjectProfileCreateRequest) -> dict[str, object]:
    try:
        profile = ProjectProfileRegistryService().create(request)
        return {"status": "ok", "profile": profile.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{project_id}")
def get_project_profile(project_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "profile": ProjectProfileRegistryService().get(project_id).model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project_profile_not_found") from exc


@router.patch("/{project_id}")
def update_project_profile(project_id: str, request: ProjectProfileUpdateRequest) -> dict[str, object]:
    try:
        return {"status": "ok", "profile": ProjectProfileRegistryService().update(project_id, request).model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project_profile_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{project_id}/validate")
def validate_project_profile(project_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "validation": ProjectProfileRegistryService().validate_profile(project_id).model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project_profile_not_found") from exc


@router.post("/{project_id}/archive")
def archive_project_profile(project_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "profile": ProjectProfileRegistryService().archive(project_id).model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project_profile_not_found") from exc


@router.post("/{project_id}/select")
def select_project_profile(project_id: str, request: dict[str, Any] | None = None) -> dict[str, object]:
    request = request or {}
    payload = ProjectProfileSelectionRequest(
        project_id=project_id,
        agent_id=request.get("agent_id"),
        session_id=request.get("session_id"),
    )
    try:
        return ProjectProfileRegistryService().select(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project_profile_not_found") from exc


@router.get("/{project_id}/commands")
def project_profile_commands(project_id: str) -> dict[str, object]:
    try:
        profile = ProjectProfileRegistryService().get(project_id)
        return {"status": "ok", "commands": [item.model_dump() for item in profile.command_profiles]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project_profile_not_found") from exc


@router.get("/{project_id}/workspaces")
def project_profile_workspaces(project_id: str) -> dict[str, object]:
    try:
        profile = ProjectProfileRegistryService().get(project_id)
        return {"status": "ok", "workspaces": [item.model_dump() for item in profile.workspace_profiles]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project_profile_not_found") from exc


@router.get("/{project_id}/health")
def project_profile_health(project_id: str) -> dict[str, object]:
    try:
        return ProjectProfileRegistryService().health(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project_profile_not_found") from exc
