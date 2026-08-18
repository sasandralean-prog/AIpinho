from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.artifacts.artifact_library import ArtifactBundleRequest, ArtifactContextUseRequest, ArtifactPreviewRequest, ArtifactQuery
from aipinho.services.artifacts.artifact_library_service import ArtifactLibraryService

router = APIRouter(prefix="/api/v1/artifact-library", tags=["artifact-library"])


@router.get("/health")
def artifact_library_health() -> dict[str, object]:
    return ArtifactLibraryService().health()


@router.get("")
def artifact_library_list(limit: int = 100, offset: int = 0) -> dict[str, object]:
    result = ArtifactLibraryService().query(ArtifactQuery(limit=limit, offset=offset))
    return result.model_dump()


@router.post("/query")
def artifact_library_query(request: ArtifactQuery) -> dict[str, object]:
    return ArtifactLibraryService().query(request).model_dump()


@router.post("/reindex")
def artifact_library_reindex() -> dict[str, object]:
    records = ArtifactLibraryService().reindex(auto_repair=True)
    return {"ok": True, "total": len(records), "items": [item.model_dump() for item in records[:100]]}


@router.post("/bundles")
def artifact_library_bundle(request: ArtifactBundleRequest) -> dict[str, object]:
    try:
        return ArtifactLibraryService().create_bundle(request).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/bundles/{bundle_artifact_id}")
def artifact_library_bundle_get(bundle_artifact_id: str) -> dict[str, object]:
    try:
        return ArtifactLibraryService().get(bundle_artifact_id).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc


@router.post("/cleanup/preview")
def artifact_library_cleanup_preview(status: str | None = None) -> dict[str, object]:
    return ArtifactLibraryService().cleanup_preview(status=status).model_dump()


@router.post("/cleanup/apply")
def artifact_library_cleanup_apply() -> dict[str, object]:
    preview = ArtifactLibraryService().cleanup_preview()
    return {"ok": True, "applied": False, "reason": "cleanup_apply_requires_explicit_confirmation_flow", "preview": preview.model_dump()}


@router.get("/{artifact_id}")
def artifact_library_get(artifact_id: str) -> dict[str, object]:
    try:
        return ArtifactLibraryService().get(artifact_id).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc


@router.post("/{artifact_id}/preview")
def artifact_library_preview(artifact_id: str, request: ArtifactPreviewRequest | None = None) -> dict[str, object]:
    try:
        effective = request or ArtifactPreviewRequest(artifact_id=artifact_id)
        if effective.artifact_id != artifact_id:
            effective = effective.model_copy(update={"artifact_id": artifact_id})
        return ArtifactLibraryService().preview(effective).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc


@router.post("/{artifact_id}/use-as-context")
def artifact_library_use_as_context(artifact_id: str, request: ArtifactContextUseRequest) -> dict[str, object]:
    try:
        effective = request if request.artifact_id == artifact_id else request.model_copy(update={"artifact_id": artifact_id})
        return ArtifactLibraryService().use_as_context(effective).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc


@router.get("/{artifact_id}/trace")
def artifact_library_trace(artifact_id: str) -> dict[str, object]:
    try:
        return ArtifactLibraryService().trace(artifact_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc


mobile_router = APIRouter(prefix="/api/v1/mobile/view-model", tags=["mobile-artifact-library"])


@mobile_router.get("/artifacts")
def mobile_artifacts() -> dict[str, object]:
    return ArtifactLibraryService().mobile_view_model()


@mobile_router.get("/artifact-library")
def mobile_artifact_library() -> dict[str, object]:
    return ArtifactLibraryService().mobile_view_model()
