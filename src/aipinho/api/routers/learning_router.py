from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.memory.learning import LearningExtractionRequest, MemoryQuery
from aipinho.services.memory.learning_memory_service import LearningMemoryService


router = APIRouter(prefix="/api/v1/learning", tags=["learning"])
mobile_router = APIRouter(prefix="/api/v1/mobile/view-model", tags=["mobile-learning"])


@router.get("/status")
def get_learning_status() -> dict[str, Any]:
    return LearningMemoryService().status().model_dump()


@router.post("/extract")
def extract_learning(request: LearningExtractionRequest) -> dict[str, Any]:
    return LearningMemoryService().extract(request).model_dump()


@router.get("/extractions/{extraction_id}")
def get_extraction(extraction_id: str) -> dict[str, Any]:
    extraction = LearningMemoryService().get_extraction(extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="learning_extraction_not_found")
    return extraction.model_dump()


@router.get("/extractions/{extraction_id}/trace")
def get_extraction_trace(extraction_id: str) -> dict[str, Any]:
    extraction = LearningMemoryService().get_extraction(extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="learning_extraction_not_found")
    return {
        "status": "ok",
        "extraction_id": extraction_id,
        "trace_refs": extraction.trace_refs,
        "blocked_reason_codes": extraction.blocked_reason_codes,
        "candidate_ids": [candidate.candidate_id for candidate in extraction.candidates],
    }


@router.get("/run-summaries")
def list_run_summaries(
    project_id: str | None = None,
    skill_pack_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    summaries = LearningMemoryService().list_run_summaries(project_id=project_id, skill_pack_id=skill_pack_id, limit=limit)
    return {"status": "ok", "run_summaries": [item.model_dump() for item in summaries]}


@router.get("/run-summaries/{run_summary_id}")
def get_run_summary(run_summary_id: str) -> dict[str, Any]:
    summary = LearningMemoryService().get_run_summary(run_summary_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="run_learning_summary_not_found")
    return summary.model_dump()


@router.get("/projects/{project_id}/profile")
def get_project_learning_profile(project_id: str) -> dict[str, Any]:
    return LearningMemoryService().project_profile(project_id).model_dump()


@router.get("/skill-packs/{skill_pack_id}/profile")
def get_skill_pack_learning_profile(skill_pack_id: str) -> dict[str, Any]:
    return LearningMemoryService().skill_pack_profile(skill_pack_id).model_dump()


@router.get("/templates/{template_id}/profile")
def get_template_learning_profile(template_id: str) -> dict[str, Any]:
    return LearningMemoryService().template_profile(template_id).model_dump()


@router.post("/query")
def query_learning_memory(request: MemoryQuery) -> dict[str, Any]:
    return LearningMemoryService().query(request)


@mobile_router.get("/learning")
def get_mobile_learning_view_model() -> dict[str, Any]:
    return LearningMemoryService().mobile_learning_view_model()


@mobile_router.get("/memory")
def get_mobile_memory_view_model() -> dict[str, Any]:
    return LearningMemoryService().mobile_memory_view_model()
