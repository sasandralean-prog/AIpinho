from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.artifacts.artifact_draft import ArtifactDraftRequest
from aipinho.schemas.artifacts.artifact_preview import ArtifactPreviewRequest
from aipinho.schemas.artifacts.artifact_source import ArtifactSource
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.artifacts.artifact_interaction_contracts import (
    ArtifactUploadRequest,
    ArtifactZipRequest,
    TaskRunArtifactExportRequest,
    UniversalArtifactCreateRequest,
)
from aipinho.schemas.artifacts.artifact_generation import ArtifactRequest
from aipinho.services.artifacts.artifact_approval_bridge import ArtifactApprovalBridge
from aipinho.services.artifacts.artifact_write_execution_service import ArtifactWriteExecutionService
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.artifacts.artifact_service_status import ArtifactServiceStatus
from aipinho.services.artifacts.artifact_writer_preview_service import ArtifactWriterPreviewService
from aipinho.services.artifacts.artifact_interaction_core import ArtifactInteractionStatusService, ArtifactMessageLinkService, ArtifactUploadService, ArtifactZipService
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.artifacts.task_run_artifact_export_service import TaskRunArtifactExportService
from aipinho.services.artifacts.artifact_generator_service import ArtifactGeneratorService

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


class SourcePreviewRequest(AIpinhoModel):
    workspace: str
    target_path: str
    format: str = "markdown"
    artifact_type: str = "report"
    title: str = ""


def _controlled_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


@router.get("/status")
def artifact_status() -> dict[str, object]:
    return {"status": "ok", "service": ArtifactServiceStatus().status(), "artifact_writer": ArtifactWriterPreviewService().status(), "artifact_write": ArtifactWriteExecutionService().status(), "interaction_artifacts": ArtifactInteractionStatusService().status()}


@router.post("")
def create_universal_artifact(request: UniversalArtifactCreateRequest) -> dict[str, object]:
    runtime = ArtifactRuntimeService()
    source = "artifact_runtime"
    compatibility_warning = None
    try:
        if runtime.can_create_from_universal_request(request):
            artifact = runtime.create_from_universal_request(request)
        else:
            source = "universal_artifact_registry_compat"
            compatibility_warning = "legacy_universal_artifact_creation_without_complete_runtime_binding"
            artifact = UniversalArtifactRegistryService().create(
                request.model_copy(
                    update={
                        "provenance": {
                            **request.provenance,
                            "artifact_runtime_compatibility": compatibility_warning,
                            "canonical_creation_source": source,
                        },
                        "metadata": {
                            **request.metadata,
                            "artifact_runtime_compatibility": compatibility_warning,
                            "canonical_creation_source": source,
                        },
                    }
                )
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise _controlled_error(exc) from exc
    return {
        "status": "ok",
        "artifact": artifact.model_dump(),
        "download_endpoint": artifact.download_endpoint,
        "requires_token": artifact.requires_token,
        "source": source,
        "compatibility_warning": compatibility_warning,
    }


@router.get("")
def list_universal_artifacts(limit: int = 200) -> dict[str, object]:
    return {"status": "ok", "artifacts": ArtifactRuntimeService().list_all(limit=limit), "source": "artifact_runtime"}


@router.get("/by-agent/{agent_id}")
def list_universal_artifacts_by_agent(agent_id: str, session_id: str | None = None, limit: int = 200) -> dict[str, object]:
    return {
        "status": "ok",
        "agent_id": agent_id,
        "session_id": session_id,
        "artifacts": ArtifactRuntimeService().by_agent(agent_id, session_id=session_id, limit=limit),
        "source": "artifact_runtime",
    }


@router.get("/by-task/{task_id}")
def list_universal_artifacts_by_task(task_id: str, limit: int = 200) -> dict[str, object]:
    lookup = ArtifactRuntimeService().by_task(task_id, limit=limit)
    return {"status": lookup.status, "task_id": task_id, "artifacts": lookup.artifacts, "count": lookup.count, "source": "artifact_runtime"}


@router.get("/by-bridge-task/{bridge_task_id}")
def list_universal_artifacts_by_bridge_task(bridge_task_id: str, limit: int = 200) -> dict[str, object]:
    return {
        "status": "ok",
        "bridge_task_id": bridge_task_id,
        "artifacts": ArtifactRuntimeService().by_bridge_task(bridge_task_id, limit=limit),
        "source": "artifact_runtime",
    }


@router.post("/drafts")
def create_draft(request: ArtifactDraftRequest) -> dict[str, object]:
    return {"status": "ok", "draft": ArtifactWriterPreviewService().create_draft(request)}


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str) -> dict[str, object]:
    draft = ArtifactWriterPreviewService().get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="artifact_draft_not_found")
    return {"status": "ok", "draft": draft}


@router.post("/previews")
def create_preview(request: ArtifactPreviewRequest) -> dict[str, object]:
    try:
        preview = ArtifactWriterPreviewService().create_preview(request)
        return {"status": "ok", "preview": preview}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/previews/from-report/{report_id}")
def create_preview_from_report(report_id: str, request: SourcePreviewRequest) -> dict[str, object]:
    source = ArtifactSource(source_type="project_report", source_id=report_id, format=request.format)  # type: ignore[arg-type]
    preview_request = ArtifactPreviewRequest(workspace=request.workspace, target_path=request.target_path, source=source, artifact_type=request.artifact_type, title=request.title)
    return create_preview(preview_request)


@router.post("/previews/from-task-run/{run_id}")
def create_preview_from_task_run(run_id: str, request: SourcePreviewRequest) -> dict[str, object]:
    source = ArtifactSource(source_type="task_run_result", source_id=run_id, format=request.format)  # type: ignore[arg-type]
    preview_request = ArtifactPreviewRequest(workspace=request.workspace, target_path=request.target_path, source=source, artifact_type=request.artifact_type, title=request.title)
    return create_preview(preview_request)


@router.post("/previews/{preview_id}/refresh-validation")
def refresh_preview_validation(preview_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "preview": ArtifactWriterPreviewService().refresh_validation(preview_id)}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/previews/{preview_id}/request-approval")
def request_preview_approval(preview_id: str) -> dict[str, object]:
    try:
        approval = ArtifactApprovalBridge().request_approval(preview_id)
        preview = ArtifactWriterPreviewService().get_preview(preview_id)
        return {"status": "ok", "approval": approval, "preview": preview}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.get("/previews/{preview_id}")
def get_preview(preview_id: str) -> dict[str, object]:
    preview = ArtifactWriterPreviewService().get_preview(preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="artifact_preview_not_found")
    return {"status": "ok", "preview": preview}


@router.get("/previews/{preview_id}/diff")
def get_preview_diff(preview_id: str) -> dict[str, object]:
    diff = ArtifactWriterPreviewService().get_diff(preview_id)
    if diff is None:
        raise HTTPException(status_code=404, detail="artifact_preview_not_found")
    return {"status": "ok", "diff": diff}


@router.get("/previews/{preview_id}/trace")
def get_preview_trace(preview_id: str) -> dict[str, object]:
    trace = ArtifactWriterPreviewService().get_trace(preview_id)
    if not trace:
        raise HTTPException(status_code=404, detail="artifact_preview_trace_not_found")
    return {"status": "ok", "trace": trace}


@router.get("/previews")
def list_previews(status: str | None = None, source_type: str | None = None, risk_level: str | None = None, approval_status: str | None = None, limit: int = 100) -> dict[str, object]:
    return {"status": "ok", "previews": ArtifactWriterPreviewService().list_previews(status=status, source_type=source_type, risk_level=risk_level, approval_status=approval_status, limit=limit)}


@router.post("/upload")
def upload_artifact(request: ArtifactUploadRequest) -> dict[str, object]:
    try:
        return {"status": "ok", "upload": ArtifactUploadService().upload(request).model_dump()}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/zip")
def create_artifact_zip(request: ArtifactZipRequest) -> dict[str, object]:
    try:
        return {"status": "ok", "zip": ArtifactZipService().create(request).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/generate")
def generate_artifact(request: ArtifactRequest) -> dict[str, object]:
    result = ArtifactGeneratorService().generate(request)
    status = "ok" if result.status in {"READY", "READY_WITH_WARNINGS"} else "blocked"
    return {"status": status, "result": result.model_dump(), "raw_default_visible": False}


@router.post("/{artifact_id}/package-evidence")
def package_artifact_evidence(artifact_id: str, filename: str | None = None) -> dict[str, object]:
    try:
        result = ArtifactGeneratorService().package_evidence(artifact_id, filename=filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc
    except ValueError as exc:
        raise _controlled_error(exc) from exc
    return {"status": "ok" if result.status in {"READY", "READY_WITH_WARNINGS"} else "blocked", "result": result.model_dump()}


@router.post("/from-task-run/{run_id}/summary-zip")
def export_task_run_summary_zip(
    run_id: str,
    request: TaskRunArtifactExportRequest,
) -> dict[str, object]:
    try:
        return {
            "status": "ok",
            "export": TaskRunArtifactExportService().export(run_id, request),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="task_run_artifact_source_not_found") from exc
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/{artifact_id}/link-to-message/{message_id}")
def link_artifact_to_message(artifact_id: str, message_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "artifact": ArtifactMessageLinkService().link_to_message(artifact_id, message_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc


@router.get("/{artifact_id}/provenance")
def get_artifact_provenance(artifact_id: str) -> dict[str, object]:
    provenance = ArtifactRuntimeService().provenance(artifact_id)
    if provenance is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return {"status": "ok", "provenance": provenance}


@router.post("/{artifact_id}/revalidate")
def revalidate_artifact(artifact_id: str) -> dict[str, object]:
    artifact = ArtifactRuntimeService().revalidate_public(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return {"status": "ok", "artifact": artifact}


@router.get("/{artifact_id}")
def get_universal_artifact(artifact_id: str) -> dict[str, object]:
    artifact = ArtifactRuntimeService().get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return {"status": "ok", "artifact": artifact}

