from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.external_workspace import (
    WorkspaceImportRequest,
    WorkspaceOnboardingRequest,
    WorkspaceRegistrationRequest,
)
from aipinho.services.workspaces.external_workspace_service import ExternalWorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


def _dump(model) -> dict[str, object]:
    return model.model_dump() if hasattr(model, "model_dump") else dict(model)


@router.get("/external/status")
def external_workspace_status() -> dict[str, object]:
    return ExternalWorkspaceService().status()


@router.post("/external/detect")
def detect_external_path(payload: dict[str, object]) -> dict[str, object]:
    candidates = ExternalWorkspaceService().detect(prompt=str(payload.get("prompt") or "") or None, path=str(payload.get("path") or "") or None)
    return {"status": "ok", "items": [_dump(item) for item in candidates], "count": len(candidates)}


@router.post("/onboarding")
def workspace_onboarding(request: WorkspaceOnboardingRequest) -> dict[str, object]:
    return _dump(ExternalWorkspaceService().onboard(request))


@router.get("/registrations")
def list_workspace_registrations() -> dict[str, object]:
    items = ExternalWorkspaceService().list_registrations()
    return {"items": [_dump(item) for item in items], "count": len(items)}


@router.post("/registrations")
def register_workspace(request: WorkspaceRegistrationRequest) -> dict[str, object]:
    return _dump(ExternalWorkspaceService().register(request))


@router.get("/registrations/{workspace_id}")
def get_workspace_registration(workspace_id: str) -> dict[str, object]:
    try:
        return _dump(ExternalWorkspaceService().get_registration(workspace_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workspace_registration_not_found") from exc


@router.post("/registrations/{workspace_id}/validate-access")
def validate_workspace_access(workspace_id: str, payload: dict[str, object]) -> dict[str, object]:
    try:
        result = ExternalWorkspaceService().validate_access(workspace_id, str(payload.get("operation") or "read"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workspace_registration_not_found") from exc
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result)
    return result


@router.post("/imports/preview")
def preview_workspace_import(request: WorkspaceImportRequest) -> dict[str, object]:
    try:
        return _dump(ExternalWorkspaceService().preview_import(request))
    except (FileNotFoundError, ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail={"ok": False, "reason_code": str(exc) or type(exc).__name__}) from exc


@router.post("/imports/{import_plan_id}/apply")
def apply_workspace_import(import_plan_id: str) -> dict[str, object]:
    try:
        return _dump(ExternalWorkspaceService().apply_import(import_plan_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workspace_import_plan_not_found") from exc


@router.post("/registrations/{workspace_id}/export")
def export_registered_source(workspace_id: str, payload: dict[str, object]) -> dict[str, object]:
    try:
        return _dump(ExternalWorkspaceService().export_registered_source(workspace_id, filename=str(payload.get("filename") or "") or None))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workspace_registration_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail={"ok": False, "reason_code": str(exc)}) from exc


@router.get("/mobile/onboarding")
def workspace_onboarding_view_model() -> dict[str, object]:
    return ExternalWorkspaceService().mobile_view_model()
