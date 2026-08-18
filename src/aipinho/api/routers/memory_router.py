from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.memory.memory_candidate import MemoryCandidateRequest
from aipinho.schemas.memory.learning import MemoryQuery, MemoryReviewRequest
from aipinho.services.memory.curated_memory_service import CuratedMemoryService
from aipinho.services.memory.learning_memory_service import LearningMemoryService
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.rag.retrieval_status_service import RetrievalStatusService
from aipinho.services.rag.integration.rag_memory_status_service import RAGMemoryStatusService

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.get("/status")
def get_memory_status() -> dict[str, Any]:
    status = MemoryCandidateService().status()
    curated = CuratedMemoryService().status()
    retrieval = RetrievalStatusService().status()
    integration = RAGMemoryStatusService().status()
    return {
        "status": "ok" if status["status"] == curated["status"] == "ok" else "degraded",
        "memory_candidate_enabled": True,
        "memory_mode": "candidate_only",
        "curated_memory_enabled": True,
        "approved_memory_enabled": True,
        "vectorstore_enabled": False,
        "embeddings_enabled": False,
        "rag_enabled": False,
        "auto_memory_enabled": False,
        "auto_prompt_memory_enabled": False,
        "auto_chat_memory_enabled": False,
        "rag_memory_integration_enabled": integration["integration_enabled"],
        "context_admission_required": True,
        "context_injection_plan_required": True,
        "candidate_layer": status,
        "curated_layer": curated,
        "curated_memory": {
            "enabled": True,
            "approved_memory_enabled": True,
            "approval_required": True,
            "candidate_required": True,
            "auto_prompt_memory_enabled": False,
            "auto_chat_memory_enabled": False,
            "status": curated["status"],
        },
        "retrieval": {
            "enabled": retrieval["retrieval_enabled"],
            "mode": retrieval["retrieval_mode"],
            "curated_memory_explicit_retrieval_enabled": True,
            "curated_memory_auto_retrieval_enabled": False,
            "prompt_auto_injection_enabled": False,
        },
        "rag_memory_integration": integration,
    }


@router.get("/candidates/status")
def get_memory_candidates_status() -> dict[str, Any]:
    return MemoryCandidateService().status()


@router.post("/candidates")
def create_memory_candidate(request: MemoryCandidateRequest) -> dict[str, Any]:
    return MemoryCandidateService().create_candidate(request).model_dump()


@router.post("/candidates/extract")
def extract_memory_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    source_type = str(payload.get("source_type") or "manual_payload")
    source_id = payload.get("source_id")
    source_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    return MemoryCandidateService().extract_candidates(source_type=source_type, source_id=source_id, payload=source_payload).model_dump()


@router.post("/candidates/from-report/{report_id}")
def extract_from_report(report_id: str) -> dict[str, Any]:
    return MemoryCandidateService().extract_candidates(source_type="project_report", source_id=report_id).model_dump()


@router.post("/candidates/from-task-run/{run_id}")
def extract_from_task_run(run_id: str) -> dict[str, Any]:
    return MemoryCandidateService().extract_candidates(source_type="task_run_result", source_id=run_id).model_dump()


@router.post("/candidates/from-validation/{validation_id}")
def extract_from_validation(validation_id: str) -> dict[str, Any]:
    return MemoryCandidateService().extract_candidates(source_type="validation_result", source_id=validation_id).model_dump()


@router.post("/candidates/from-patch-apply/{apply_run_id}")
def extract_from_patch_apply(apply_run_id: str) -> dict[str, Any]:
    return MemoryCandidateService().extract_candidates(source_type="patch_apply_result", source_id=apply_run_id).model_dump()


@router.post("/candidates/{candidate_id}/refresh-validation")
def refresh_candidate_validation(candidate_id: str) -> dict[str, Any]:
    candidate = MemoryCandidateService().refresh_validation(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    return {"status": candidate.status, "candidate": candidate}


@router.post("/candidates/{candidate_id}/reject")
def reject_candidate(candidate_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    learning = LearningMemoryService()
    learning_candidate = learning.get_candidate(candidate_id)
    if learning_candidate is not None:
        request = MemoryReviewRequest(**(payload or {}))
        candidate = learning.reject_candidate(candidate_id, reviewed_by=request.reviewed_by, reason=request.reason)
        return {"status": candidate.status, "candidate": candidate.model_dump(), "candidate_layer": "learning"}
    candidate = MemoryCandidateService().reject_candidate(candidate_id, str((payload or {}).get("reason") or "user_rejected"))
    if candidate is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    return {"status": candidate.status, "candidate": candidate}


@router.post("/candidates/{candidate_id}/accept")
def accept_learning_candidate(candidate_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    service = LearningMemoryService()
    if service.get_candidate(candidate_id) is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    request = MemoryReviewRequest(**(payload or {}))
    return service.accept_candidate(candidate_id, reviewed_by=request.reviewed_by, reason=request.reason)


@router.post("/candidates/{candidate_id}/archive")
def archive_learning_candidate(candidate_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    service = LearningMemoryService()
    if service.get_candidate(candidate_id) is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    request = MemoryReviewRequest(**(payload or {}))
    candidate = service.archive_candidate(candidate_id, reviewed_by=request.reviewed_by, reason=request.reason)
    return {"status": candidate.status, "candidate": candidate.model_dump(), "candidate_layer": "learning"}


@router.post("/candidates/{candidate_id}/mark-stale")
def mark_learning_candidate_stale(candidate_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    service = LearningMemoryService()
    if service.get_candidate(candidate_id) is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    request = MemoryReviewRequest(**(payload or {}))
    candidate = service.mark_stale(candidate_id, reviewed_by=request.reviewed_by, reason=request.reason)
    return {"status": candidate.status, "candidate": candidate.model_dump(), "candidate_layer": "learning"}


@router.post("/candidates/{candidate_id}/mark-duplicate")
def mark_duplicate(candidate_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    candidate = MemoryCandidateService().mark_duplicate(candidate_id, duplicate_of=payload.get("duplicate_of"), reason=str(payload.get("reason") or "marked_duplicate"))
    if candidate is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    return {"status": candidate.status, "candidate": candidate}


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str) -> dict[str, Any]:
    learning_candidate = LearningMemoryService().get_candidate(candidate_id)
    if learning_candidate is not None:
        return {"status": learning_candidate.status, "candidate": learning_candidate.model_dump(), "candidate_layer": "learning"}
    candidate = MemoryCandidateService().get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    return {"status": candidate.status, "candidate": candidate}


@router.get("/candidates/{candidate_id}/evidence")
def get_candidate_evidence(candidate_id: str) -> dict[str, Any]:
    service = MemoryCandidateService()
    if service.get_candidate(candidate_id) is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    return {"status": "ok", "candidate_id": candidate_id, "evidence": service.get_evidence(candidate_id)}


@router.get("/candidates/{candidate_id}/trace")
def get_candidate_trace(candidate_id: str) -> dict[str, Any]:
    learning_candidate = LearningMemoryService().get_candidate(candidate_id)
    if learning_candidate is not None:
        return {
            "status": "ok",
            "candidate_id": candidate_id,
            "candidate_layer": "learning",
            "trace": {
                "source_refs": learning_candidate.source_refs,
                "evidence_refs": learning_candidate.evidence_refs,
                "block_reason_codes": learning_candidate.block_reason_codes,
                "warnings": learning_candidate.warnings,
            },
        }
    service = MemoryCandidateService()
    if service.get_candidate(candidate_id) is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    return {"status": "ok", "candidate_id": candidate_id, "trace": service.get_trace(candidate_id)}


@router.get("/candidates/{candidate_id}/events")
def get_candidate_events(candidate_id: str) -> dict[str, Any]:
    service = MemoryCandidateService()
    if service.get_candidate(candidate_id) is None:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found")
    return {"status": "ok", "candidate_id": candidate_id, "events": service.get_events(candidate_id)}


@router.get("/candidates")
def list_memory_candidates(
    status: str | None = None,
    kind: str | None = None,
    scope: str | None = None,
    source_type: str | None = None,
    risk_level: str | None = None,
    confidence: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    candidates = MemoryCandidateService().list_candidates(status=status, kind=kind, scope=scope, source_type=source_type, risk_level=risk_level, confidence=confidence, limit=limit)
    learning_candidates = LearningMemoryService().list_candidates(status=status, type=kind, project_id=None, include_all=False, limit=limit)
    return {
        "status": "ok",
        "candidates": candidates,
        "learning_candidates": [candidate.model_dump() for candidate in learning_candidates],
        "candidate_layers": ["legacy_memory_candidate", "learning_from_runs"],
    }


@router.post("/query")
def query_learning_memory(request: MemoryQuery) -> dict[str, Any]:
    return LearningMemoryService().query(request)


@router.get("/namespaces")
def get_learning_memory_namespaces() -> dict[str, Any]:
    return LearningMemoryService().namespaces()


@router.get("/project/{project_id}")
def get_project_memory_profile(project_id: str) -> dict[str, Any]:
    return LearningMemoryService().project_profile(project_id).model_dump()


@router.get("/skill-pack/{skill_pack_id}")
def get_skill_pack_memory_profile(skill_pack_id: str) -> dict[str, Any]:
    return LearningMemoryService().skill_pack_profile(skill_pack_id).model_dump()


@router.get("/template/{template_id}")
def get_template_memory_profile(template_id: str) -> dict[str, Any]:
    return LearningMemoryService().template_profile(template_id).model_dump()


@router.post("/approve")
def approve_memory_blocked(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "blocked",
        "approved": False,
        "reason": "approved_memory_disabled_until_future_sprint",
        "message": "Nesta sprint so e permitido criar candidato de memoria pendente de aprovacao futura.",
        "payload": payload,
    }


@router.post("/reject")
def reject_memory_compat(payload: dict[str, Any]) -> dict[str, Any]:
    candidate_id = payload.get("candidate_id")
    if candidate_id:
        candidate = MemoryCandidateService().reject_candidate(str(candidate_id), str(payload.get("reason") or "compat_reject"))
        return {"status": candidate.status if candidate else "not_found", "candidate": candidate}
    return {"status": "needs_candidate_id", "rejected": False}


@router.get("/search")
def search_memory(query: str | None = None) -> dict[str, Any]:
    return {
        "status": "candidate_only",
        "query": query,
        "results": [],
        "approved_memory_enabled": False,
        "message": "Busca de memoria definitiva ainda nao esta habilitada; use /api/v1/memory/candidates.",
    }
