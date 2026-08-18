from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.vision.contracts import VisionRAGIngestionRequest, VisionRAGQueryRequest
from aipinho.services.vision.vision_rag_ingestion_preview_service import VisionRAGIngestionPreviewService
from aipinho.services.vision.vision_rag_namespace_service import VisionRAGNamespaceService
from aipinho.services.vision.vision_rag_query_service import VisionRAGQueryService
from aipinho.services.vision.vision_status_service import VisionStatusService

router = APIRouter(prefix="/api/v1/vision-rag", tags=["vision-rag"])


@router.get("/status")
def get_status() -> dict[str, object]:
    status = VisionStatusService().status()
    return {"status": status.get("status", "ok"), "vision_rag": status}


@router.get("/namespaces")
def list_namespaces() -> dict[str, object]:
    service = VisionRAGNamespaceService()
    return service.status()


@router.post("/ingest-preview")
def ingest_preview(request: VisionRAGIngestionRequest) -> dict[str, object]:
    preview = VisionRAGIngestionPreviewService().preview(request)
    return {
        "status": preview.status,
        "preview_id": preview.preview_id,
        "ingestion_id": preview.ingestion_id,
        "chunk_count": preview.chunk_count,
        "approval_required": preview.approval_required,
        "would_write_index": preview.would_write_index,
        "preview": preview.model_dump(),
    }


@router.post("/query")
def query(request: VisionRAGQueryRequest) -> dict[str, object]:
    result = VisionRAGQueryService().query(request)
    return {"status": result.status, "query_id": result.query_id, "hits": [hit.model_dump() for hit in result.hits], "context_bundle": result.context_bundle.model_dump() if result.context_bundle else None, "result": result.model_dump()}
