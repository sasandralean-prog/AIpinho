from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from aipinho.schemas.rag.retrieval_request import Citation, RetrievalRequest
from aipinho.services.rag.retrieval_service import RetrievalService
from aipinho.services.rag.retrieval_source_registry import RetrievalSourceRegistry
from aipinho.services.rag.source_ref_validator import SourceRefValidator

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


@router.get("/status")
def get_rag_status() -> dict[str, Any]:
    return RetrievalService().status()


@router.get("/sources")
def list_sources() -> dict[str, Any]:
    return {"status": "ok", "sources": [source.model_dump() for source in RetrievalSourceRegistry().list_sources(include_blocked=True)]}


@router.get("/sources/{source_id}")
def get_source(source_id: str) -> dict[str, Any]:
    source = RetrievalSourceRegistry().get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="retrieval_source_not_found")
    return {"status": "ok" if source.enabled else "blocked", "source": source}


@router.post("/retrieve")
def retrieve(request: RetrievalRequest) -> dict[str, Any]:
    return RetrievalService().retrieve(request).model_dump()


@router.post("/retrieve/files")
def retrieve_files(request: RetrievalRequest) -> dict[str, Any]:
    request.sources = ["project_files"]
    request.explicit = True
    return RetrievalService().retrieve(request).model_dump()


@router.post("/retrieve/reports")
def retrieve_reports(request: RetrievalRequest) -> dict[str, Any]:
    request.sources = ["project_reports"]
    request.explicit = True
    return RetrievalService().retrieve(request).model_dump()


@router.post("/retrieve/memory")
def retrieve_memory(request: RetrievalRequest) -> dict[str, Any]:
    request.sources = ["curated_memory"]
    request.explicit = True
    return RetrievalService().retrieve(request).model_dump()


@router.post("/context-bundle")
def context_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("retrieval_id"):
        stored = RetrievalService().get_retrieval(str(payload["retrieval_id"]))
        if not stored:
            raise HTTPException(status_code=404, detail="retrieval_not_found")
        return {"status": stored.get("status"), "context_bundle": stored.get("context_bundle")}
    request = RetrievalRequest.model_validate(payload) if hasattr(RetrievalRequest, "model_validate") else RetrievalRequest.parse_obj(payload)
    result = RetrievalService().retrieve(request)
    return {"status": result.status, "context_bundle": result.context_bundle.model_dump() if result.context_bundle else None}


@router.post("/evidence-bundle")
def evidence_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("retrieval_id"):
        stored = RetrievalService().get_retrieval(str(payload["retrieval_id"]))
        if not stored:
            raise HTTPException(status_code=404, detail="retrieval_not_found")
        return {"status": stored.get("status"), "evidence_bundle": stored.get("evidence_bundle")}
    request = RetrievalRequest.model_validate(payload) if hasattr(RetrievalRequest, "model_validate") else RetrievalRequest.parse_obj(payload)
    result = RetrievalService().retrieve(request)
    return {"status": result.status, "evidence_bundle": result.evidence_bundle.model_dump() if result.evidence_bundle else None}


@router.post("/validate-citations")
def validate_citations(payload: dict[str, Any]) -> dict[str, Any]:
    validator = SourceRefValidator()
    raw_citations = payload.get("citations") or []
    citations = []
    for item in raw_citations:
        try:
            citations.append(Citation.model_validate(item) if hasattr(Citation, "model_validate") else Citation.parse_obj(item))
        except Exception:
            citations.append(None)
    checks = [validator.validate_citation(citation) for citation in citations]
    valid = bool(checks) and all(check.get("valid") for check in checks)
    return {"status": "ok" if valid else "blocked", "valid": valid, "checks": checks}


@router.get("/retrievals/{retrieval_id}")
def get_retrieval(retrieval_id: str) -> dict[str, Any]:
    result = RetrievalService().get_retrieval(retrieval_id)
    if result is None:
        raise HTTPException(status_code=404, detail="retrieval_not_found")
    return result


@router.get("/retrievals/{retrieval_id}/trace")
def get_retrieval_trace(retrieval_id: str) -> dict[str, Any]:
    result = RetrievalService().get_retrieval(retrieval_id)
    if result is None:
        raise HTTPException(status_code=404, detail="retrieval_not_found")
    return {"status": result.get("status"), "retrieval_id": retrieval_id, "trace": result.get("trace", [])}


@router.get("/retrievals")
def list_retrievals(limit: int = 100) -> dict[str, Any]:
    return {"status": "ok", "retrievals": RetrievalService().list_retrievals(limit=limit)}


@router.post("/query")
def query_rag(payload: dict[str, Any]):
    request = RetrievalRequest(query=str(payload.get("query") or payload.get("text") or ""), sources=list(payload.get("sources") or ["project_reports"]), explicit=bool(payload.get("explicit", True)), workspace=payload.get("workspace"))
    return RetrievalService().retrieve(request).model_dump()


@router.post("/ingest")
def ingest_rag(payload: dict[str, Any]):
    return {"ok": False, "status": "blocked", "ingested": False, "blocked_reasons": ["automatic_ingestion_disabled", "vectorstore_creation_disabled"], "payload": {"source": payload.get("source")}}
