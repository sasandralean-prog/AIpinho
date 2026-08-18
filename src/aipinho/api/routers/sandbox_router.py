from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.sandbox import (
    SandboxArtifactExportRequest,
    SandboxCleanupPreviewRequest,
    SandboxFileRequest,
    SandboxShellRequest,
)
from aipinho.schemas.sandbox_autopilot import SandboxAutopilotRequest
from aipinho.schemas.project_generation import ProjectGenerationRequest
from aipinho.services.sandbox.sandbox_project_factory import SandboxProjectFactory
from aipinho.services.sandbox.sandbox_autopilot_service import SandboxAutopilotService
from aipinho.services.sandbox.sandbox_artifact_service import SandboxArtifactService
from aipinho.services.sandbox.sandbox_cleanup_service import SandboxCleanupService
from aipinho.services.sandbox.sandbox_file_service import SandboxFileService
from aipinho.services.sandbox.sandbox_shell_service import SandboxShellService
from aipinho.services.sandbox.sandbox_view_model_service import SandboxViewModelService
from aipinho.services.sandbox.sandbox_validation_service import SandboxValidationService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService

router = APIRouter(prefix="/api/v1/sandbox", tags=["sandbox"])


def _dump(model) -> dict[str, object]:
    return model.model_dump() if hasattr(model, "model_dump") else dict(model)


def _policy_error(exc: PermissionError) -> HTTPException:
    reason = str(exc) or "sandbox_policy_blocked"
    return HTTPException(status_code=409, detail={"ok": False, "reason_code": reason, "status": "blocked"})


@router.get("/status")
def sandbox_status() -> dict[str, object]:
    return _dump(SandboxWorkspaceService().status())


@router.get("/health")
def sandbox_health() -> dict[str, object]:
    return SandboxWorkspaceService().health()


@router.post("/project-factory/classify")
def sandbox_project_factory_classify(payload: dict[str, object]) -> dict[str, object]:
    decision = SandboxProjectFactory().classify_goal(str(payload.get("user_goal") or payload.get("prompt") or ""))
    return _dump(decision)


@router.post("/project-factory/generate")
def sandbox_project_factory_generate(request: ProjectGenerationRequest) -> dict[str, object]:
    try:
        return _dump(SandboxProjectFactory().generate(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="sandbox_workspace_or_task_not_found") from exc


@router.get("/autopilot/status")
def sandbox_autopilot_status() -> dict[str, object]:
    return SandboxAutopilotService().status()


@router.post("/autopilot/route")
def sandbox_autopilot_route(request: SandboxAutopilotRequest) -> dict[str, object]:
    return _dump(SandboxAutopilotService().route(request))


@router.post("/autopilot/run")
def sandbox_autopilot_run(request: SandboxAutopilotRequest) -> dict[str, object]:
    try:
        return _dump(SandboxAutopilotService().run(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="sandbox_workspace_or_task_not_found") from exc


@router.get("/policy")
def sandbox_policy() -> dict[str, object]:
    return SandboxWorkspaceService().policy.status()


@router.get("/workspaces")
def list_sandbox_workspaces() -> dict[str, object]:
    workspaces = SandboxWorkspaceService().list_workspaces()
    return {"items": [_dump(item) for item in workspaces], "count": len(workspaces)}


@router.post("/workspaces")
def create_sandbox_workspace(payload: dict[str, object]) -> dict[str, object]:
    name = str(payload.get("name") or "workspace")
    role = str(payload.get("role") or "sandbox_mutable")
    return _dump(SandboxWorkspaceService().create_workspace(name, role=role))


@router.get("/workspaces/{sandbox_workspace_id}")
def get_sandbox_workspace(sandbox_workspace_id: str) -> dict[str, object]:
    try:
        return _dump(SandboxWorkspaceService().get_workspace(sandbox_workspace_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="sandbox_workspace_not_found") from exc


@router.get("/tasks")
def list_sandbox_tasks() -> dict[str, object]:
    tasks = SandboxWorkspaceService().list_tasks()
    return {"items": [_dump(item) for item in tasks], "count": len(tasks)}


@router.post("/tasks")
def create_sandbox_task(payload: dict[str, object]) -> dict[str, object]:
    try:
        task = SandboxWorkspaceService().create_task(
            sandbox_workspace_id=str(payload.get("sandbox_workspace_id") or "sandbox_ws_default"),
            title=str(payload.get("title") or "Sandbox task"),
            created_by_agent_id=str(payload.get("created_by_agent_id")) if payload.get("created_by_agent_id") else None,
        )
        return _dump(task)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="sandbox_workspace_not_found") from exc


@router.get("/tasks/{sandbox_task_id}")
def get_sandbox_task(sandbox_task_id: str) -> dict[str, object]:
    try:
        return _dump(SandboxWorkspaceService().get_task(sandbox_task_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="sandbox_task_not_found") from exc


@router.post("/tasks/{sandbox_task_id}/cancel")
def cancel_sandbox_task(sandbox_task_id: str) -> dict[str, object]:
    try:
        return _dump(SandboxWorkspaceService().cancel_task(sandbox_task_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="sandbox_task_not_found") from exc


@router.post("/files/list")
def sandbox_list_files(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return SandboxFileService().list_files(request)
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/files/read")
def sandbox_read_file(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return SandboxFileService().read_file(request)
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/files/write")
def sandbox_write_file(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return _dump(SandboxFileService().write_file(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/files/append")
def sandbox_append_file(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return _dump(SandboxFileService().write_file(request, append=True))
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/files/modify")
def sandbox_modify_file(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return _dump(SandboxFileService().modify_file(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/files/mkdir")
def sandbox_mkdir(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return _dump(SandboxFileService().mkdir(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/files/copy")
def sandbox_copy(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return _dump(SandboxFileService().copy(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/files/move")
def sandbox_move(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return _dump(SandboxFileService().move(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/files/delete-safe")
def sandbox_delete_safe(request: SandboxFileRequest) -> dict[str, object]:
    try:
        return _dump(SandboxFileService().delete_safe(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/shell/run")
def sandbox_shell_run(request: SandboxShellRequest) -> dict[str, object]:
    return _dump(SandboxShellService().run(request))


@router.post("/artifacts/export")
def sandbox_artifact_export(request: SandboxArtifactExportRequest) -> dict[str, object]:
    try:
        return _dump(SandboxArtifactService().export_zip(request))
    except PermissionError as exc:
        raise _policy_error(exc) from exc


@router.post("/validate")
def sandbox_validate(payload: dict[str, object]) -> dict[str, object]:
    return _dump(
        SandboxValidationService().validate(
            sandbox_workspace_id=str(payload.get("sandbox_workspace_id") or "sandbox_ws_default"),
            sandbox_task_id=str(payload.get("sandbox_task_id")) if payload.get("sandbox_task_id") else None,
            relative_paths=[str(item) for item in (payload.get("relative_paths") or [])],
            artifact_ids=[str(item) for item in (payload.get("artifact_ids") or [])],
        )
    )


@router.get("/artifacts")
def sandbox_artifacts() -> dict[str, object]:
    exports = SandboxArtifactService().list_exports()
    return {"items": [_dump(item) for item in exports], "count": len(exports)}


@router.get("/artifacts/{artifact_export_id}")
def sandbox_artifact(artifact_export_id: str) -> dict[str, object]:
    try:
        return _dump(SandboxArtifactService().get_export(artifact_export_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="sandbox_artifact_not_found") from exc


@router.post("/cleanup/preview")
def sandbox_cleanup_preview(request: SandboxCleanupPreviewRequest) -> dict[str, object]:
    return _dump(SandboxCleanupService().preview(request))


@router.post("/cleanup/apply")
def sandbox_cleanup_apply(payload: dict[str, object]) -> dict[str, object]:
    return SandboxCleanupService().apply(str(payload.get("cleanup_preview_id") or ""))


@router.get("/tasks/{sandbox_task_id}/trace")
def sandbox_task_trace(sandbox_task_id: str) -> dict[str, object]:
    return {"task_id": sandbox_task_id, "events": SandboxWorkspaceService().store.list_trace(sandbox_task_id)}


@router.get("/view-model")
def sandbox_view_model() -> dict[str, object]:
    return SandboxViewModelService().view_model()
