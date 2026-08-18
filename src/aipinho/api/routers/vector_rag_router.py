from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.rag.vector.contracts import RAGIngestionRequest, RAGQueryRequest, RerankRequest
from aipinho.services.rag.vector.rag_index_doctor_service import RAGIndexDoctorService
from aipinho.services.rag.vector.rag_ingestion_approval_service import RAGIngestionApprovalService
from aipinho.services.rag.vector.rag_ingestion_executor import RAGIngestionExecutor
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService
from aipinho.services.rag.vector.rag_rerank_service import RAGRerankService
from aipinho.services.rag.vector.rag_vector_query_service import RAGVectorQueryService
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry
from aipinho.services.rag.vector.vector_index_store import VectorIndexStore
from aipinho.services.rag.vector.vector_namespace_service import VectorNamespaceService
from aipinho.services.rag.vector.vector_rag_status_service import VectorRAGStatusService
from aipinho.services.rag.vector.vector_rag_trace_service import VectorRAGTraceService

router = APIRouter(prefix="/api/v1/vector-rag", tags=["vector-rag"])


@router.get("/status")
def get_vector_rag_status() -> dict[str, object]:
    return VectorRAGStatusService().status()


@router.get("/namespaces")
def list_namespaces() -> dict[str, object]:
    namespaces = VectorNamespaceService().list_namespaces(include_disabled=True)
    return {"status": "ok", "namespaces": [namespace.model_dump() for namespace in namespaces]}


@router.get("/namespaces/{namespace_id}")
def get_namespace(namespace_id: str) -> dict[str, object]:
    namespace = VectorNamespaceService().get_namespace(namespace_id)
    if namespace is None:
        raise HTTPException(status_code=404, detail="namespace_not_found")
    return {"status": "ok" if namespace.enabled else "blocked", "namespace": namespace.model_dump()}


@router.get("/indexes")
def list_indexes() -> dict[str, object]:
    registry = VectorIndexRegistry()
    store = VectorIndexStore()
    indexes = [store.index(namespace).model_dump() for namespace in registry.list_namespaces(include_disabled=True)]
    return {"status": "ok", "indexes": indexes}


@router.get("/indexes/{namespace_id}/doctor")
def doctor_index(namespace_id: str) -> dict[str, object]:
    return RAGIndexDoctorService().doctor(namespace_id)


@router.post("/ingest-preview")
def ingest_preview(request: RAGIngestionRequest) -> dict[str, object]:
    preview = RAGIngestionPreviewService().preview(request)
    return {
        "status": preview.status,
        "preview_id": preview.preview_id,
        "ingestion_id": preview.ingestion_id,
        "chunk_count": preview.chunk_count,
        "approval_required": preview.approval_required,
        "preview": preview.model_dump(),
        "would_write_index": False,
    }


@router.post("/ingest-approval")
def ingest_approval(payload: dict[str, object]) -> dict[str, object]:
    preview_id = str(payload.get("preview_id") or "")
    service = RAGIngestionApprovalService()
    result = service.create_approval(preview_id, reason=str(payload.get("reason") or ""))
    if result.get("status") == "ok" and bool(payload.get("approve", False)):
        approval = result.get("approval", {})
        if isinstance(approval, dict):
            result = service.approve(str(approval.get("approval_id")))
    return result


@router.post("/ingest-execute")
def ingest_execute(payload: dict[str, object]) -> dict[str, object]:
    result = RAGIngestionExecutor().execute(preview_id=str(payload.get("preview_id") or ""), approval_id=str(payload.get("approval_id") or ""))
    return {
        "status": result.status,
        "ingestion_id": result.ingestion_id,
        "chunks_indexed": result.chunks_indexed,
        "embeddings_saved": result.embeddings_saved,
        "citations_saved": result.citations_saved,
        "result": result.model_dump(),
    }


@router.post("/query")
def query_vector_rag(request: RAGQueryRequest) -> dict[str, object]:
    result = RAGVectorQueryService().query(request)
    return {"status": result.status, "query_id": result.query_id, "hits": [hit.model_dump() for hit in result.hits], "context_bundle": result.context_bundle.model_dump() if result.context_bundle else None, "result": result.model_dump()}


@router.post("/query/role/{role_id}")
def query_role_rag(role_id: str, payload: dict[str, object]) -> dict[str, object]:
    request = RAGQueryRequest(query=str(payload.get("query") or ""), role_id=role_id, top_k=int(payload.get("top_k", 5)), use_global_context=bool(payload.get("use_global_context", True)))
    result = RAGVectorQueryService().query(request)
    return {"status": result.status, "query_id": result.query_id, "hits": [hit.model_dump() for hit in result.hits], "context_bundle": result.context_bundle.model_dump() if result.context_bundle else None, "result": result.model_dump()}


@router.post("/query/global")
def query_global_rag(payload: dict[str, object]) -> dict[str, object]:
    request = RAGQueryRequest(query=str(payload.get("query") or ""), namespace_id="global_ecosystem", top_k=int(payload.get("top_k", 5)), use_global_context=False)
    result = RAGVectorQueryService().query(request)
    return {"status": result.status, "query_id": result.query_id, "hits": [hit.model_dump() for hit in result.hits], "context_bundle": result.context_bundle.model_dump() if result.context_bundle else None, "result": result.model_dump()}


@router.post("/rerank")
def rerank_hits(request: RerankRequest) -> dict[str, object]:
    result = RAGRerankService().rerank(request)
    return {"status": result.status, "result": result.model_dump()}


@router.get("/ingestions/{ingestion_id}")
def get_ingestion(ingestion_id: str) -> dict[str, object]:
    result = RAGIngestionExecutor().get_result(ingestion_id)
    if result is None:
        raise HTTPException(status_code=404, detail="ingestion_not_found")
    return {"status": result.get("status", "ok"), "ingestion": result}


@router.get("/ingestions/{ingestion_id}/trace")
def get_ingestion_trace(ingestion_id: str) -> dict[str, object]:
    result = RAGIngestionExecutor().get_result(ingestion_id)
    if result is None:
        raise HTTPException(status_code=404, detail="ingestion_not_found")
    trace_id = result.get("trace_id")
    return {"status": "ok" if trace_id else "missing", "trace": VectorRAGTraceService().get(str(trace_id)) if trace_id else None}


@router.get("/queries/{query_id}")
def get_query(query_id: str) -> dict[str, object]:
    result = RAGVectorQueryService().get_query(query_id)
    if result is None:
        raise HTTPException(status_code=404, detail="query_not_found")
    return {"status": result.get("status", "ok"), "query": result}


@router.get("/queries/{query_id}/trace")
def get_query_trace(query_id: str) -> dict[str, object]:
    result = RAGVectorQueryService().get_query(query_id)
    if result is None:
        raise HTTPException(status_code=404, detail="query_not_found")
    trace_id = result.get("trace_id")
    return {"status": "ok" if trace_id else "missing", "trace": VectorRAGTraceService().get(str(trace_id)) if trace_id else None}
