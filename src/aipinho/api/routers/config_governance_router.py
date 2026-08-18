from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.config_governance.config_change import ConfigChangeRequest
from aipinho.schemas.config_governance.workspace_permission import WorkspaceEntry, WorkspacePreviewRequest
from aipinho.services.config_governance.config_governance_service import ConfigGovernanceService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.security.local_token_service import LocalTokenService

router = APIRouter(prefix="/api/v1/config", tags=["config-governance"])


def _service() -> ConfigGovernanceService:
    return ConfigGovernanceService()


def _matrix() -> WorkspacePermissionMatrixService:
    return WorkspacePermissionMatrixService().load()


def _require_token(authorization: str | None) -> None:
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="local_token_required")


def _raise_value_error(exc: ValueError) -> None:
    detail = str(exc)
    status = 404 if detail.endswith("_not_found") or detail == "backup_not_found" else 409
    raise HTTPException(status_code=status, detail=detail) from exc


@router.get("/effective-policy")
def get_effective_policy() -> dict[str, object]:
    return _service().effective_policy()


@router.get("/workspaces")
def list_workspaces() -> dict[str, object]:
    return {"status": "ok", "workspaces": _matrix().list_workspaces()}


@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str) -> dict[str, object]:
    workspace = _matrix().get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return {"status": "ok", "workspace": workspace}


@router.post("/workspaces")
def add_workspace(entry: WorkspaceEntry, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    request = ConfigChangeRequest(
        target="workspace_registry",
        operation="add_workspace",
        payload={"workspace": entry.model_dump()},
        reason="workspace_config_change_requested",
    )
    change = _service().create_change(request)
    preview = _service().preview_change(change.change_id)
    return {"status": "ok", "change": change.model_dump(), "preview": preview.model_dump()}


@router.patch("/workspaces/{workspace_id}")
def update_workspace(workspace_id: str, entry: WorkspaceEntry, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    payload = entry.model_dump()
    payload["workspace_id"] = workspace_id
    request = ConfigChangeRequest(
        target="workspace_registry",
        operation="update_workspace",
        payload={"workspace": payload},
        reason="workspace_config_change_requested",
    )
    change = _service().create_change(request)
    preview = _service().preview_change(change.change_id)
    return {"status": "ok", "change": change.model_dump(), "preview": preview.model_dump()}


@router.post("/workspaces/{workspace_id}/enable")
def enable_workspace(workspace_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        candidate = _matrix().set_enabled(workspace_id, True)
    except ValueError as exc:
        _raise_value_error(exc)
    request = ConfigChangeRequest(target="workspace_registry", operation="replace", payload=candidate, reason="workspace_enabled")
    change = _service().create_change(request)
    preview = _service().preview_change(change.change_id)
    return {"status": "ok", "change": change.model_dump(), "preview": preview.model_dump()}


@router.post("/workspaces/{workspace_id}/disable")
def disable_workspace(workspace_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        candidate = _matrix().set_enabled(workspace_id, False)
    except ValueError as exc:
        _raise_value_error(exc)
    request = ConfigChangeRequest(target="workspace_registry", operation="replace", payload=candidate, reason="workspace_disabled")
    change = _service().create_change(request)
    preview = _service().preview_change(change.change_id)
    return {"status": "ok", "change": change.model_dump(), "preview": preview.model_dump()}


@router.get("/workspace-roles")
def get_workspace_roles() -> dict[str, object]:
    return {"status": "ok", "roles": list(_matrix().role_defaults().keys())}


@router.get("/permission-matrix")
def get_permission_matrix() -> dict[str, object]:
    matrix = _matrix()
    return {"status": "ok", "role_defaults": matrix.role_defaults(), "workspaces": matrix.list_workspaces()}


@router.post("/workspaces/{workspace_id}/permissions")
def update_workspace_permissions(workspace_id: str, permissions: dict[str, str], authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        candidate = _matrix().set_permissions(workspace_id, permissions)
    except ValueError as exc:
        _raise_value_error(exc)
    request = ConfigChangeRequest(target="workspace_registry", operation="replace", payload=candidate, reason="permission_matrix_updated")
    change = _service().create_change(request)
    preview = _service().preview_change(change.change_id)
    return {"status": "ok", "change": change.model_dump(), "preview": preview.model_dump()}


@router.post("/workspaces/preview")
def preview_workspace(request: WorkspacePreviewRequest) -> dict[str, object]:
    return _matrix().preview_workspace(request)


@router.get("/providers")
def get_providers_config() -> dict[str, object]:
    service = _service()
    path = service.target_path("provider_policy")
    return {"status": "ok", "target": "provider_policy", "path": str(path), "exists": path.exists()}


@router.get("/agents")
def get_agents_config() -> dict[str, object]:
    service = _service()
    path = service.target_path("agent_registry")
    return {"status": "ok", "target": "agent_registry", "path": str(path), "exists": path.exists()}


@router.get("/permissions")
def get_permissions_config() -> dict[str, object]:
    return get_permission_matrix()


@router.post("/changes")
def create_config_change(request: ConfigChangeRequest, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    change = _service().create_change(request)
    return {"status": "ok" if change.status != "failed" else "failed", "change": change.model_dump()}


@router.get("/changes")
def list_config_changes() -> dict[str, object]:
    return {"status": "ok", "changes": [change.model_dump() for change in _service().list_changes()]}


@router.get("/changes/{change_id}")
def get_config_change(change_id: str) -> dict[str, object]:
    change = _service().get_change(change_id)
    if change is None:
        raise HTTPException(status_code=404, detail="config_change_not_found")
    return {"status": "ok", "change": change.model_dump()}


@router.post("/changes/{change_id}/preview")
def preview_config_change(change_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        preview = _service().preview_change(change_id)
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok" if preview.validation_status == "ok" else "failed", "preview": preview.model_dump()}


@router.post("/changes/{change_id}/approve")
def approve_config_change(change_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        change = _service().approve_change(change_id, actor=Actor(type="user", id="local_user"))
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok", "change": change.model_dump()}


@router.post("/changes/{change_id}/apply")
def apply_config_change(change_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        result = _service().apply_change(change_id)
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok" if result.status == "applied" else "failed", "result": result.model_dump()}


@router.post("/changes/{change_id}/cancel")
def cancel_config_change(change_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        change = _service().cancel_change(change_id)
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok", "change": change.model_dump()}


@router.get("/backups")
def list_config_backups() -> dict[str, object]:
    return {"status": "ok", "backups": [backup.model_dump() for backup in _service().list_backups()]}


@router.get("/backups/{backup_id}")
def get_config_backup(backup_id: str) -> dict[str, object]:
    backup = _service().get_backup(backup_id)
    if backup is None:
        raise HTTPException(status_code=404, detail="backup_not_found")
    return {"status": "ok", "backup": backup.model_dump()}


@router.post("/rollback/{backup_id}")
def rollback_config(backup_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        result = _service().rollback(backup_id)
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok", "result": result.model_dump()}


@router.post("/reload")
def reload_config(authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    return _service().reload()


@router.get("/health")
def get_config_health() -> dict[str, object]:
    return _service().health()
