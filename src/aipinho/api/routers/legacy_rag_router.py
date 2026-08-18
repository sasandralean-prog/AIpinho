
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from aipinho.services.legacy_rag.legacy_core import LegacyRAGPipelineService

router = APIRouter(prefix="/api/v1/legacy-rag", tags=["legacy-rag"])


@router.get("/status")
def status() -> dict[str, object]:
    return LegacyRAGPipelineService().status().model_dump()


@router.post("/scan")
def scan() -> dict[str, object]:
    return LegacyRAGPipelineService().scan().model_dump()


@router.post("/sanitize")
def sanitize() -> dict[str, object]:
    return LegacyRAGPipelineService().sanitize().model_dump()


@router.post("/classify")
def classify() -> dict[str, object]:
    return LegacyRAGPipelineService().classify().model_dump()


@router.post("/detect-conflicts")
def detect_conflicts() -> dict[str, object]:
    return LegacyRAGPipelineService().detect_conflicts().model_dump()


@router.post("/review/summary")
def review_summary() -> dict[str, object]:
    return LegacyRAGPipelineService().review_summary().model_dump()


@router.post("/import/preview")
def import_preview() -> dict[str, object]:
    return LegacyRAGPipelineService().import_preview().model_dump()


@router.post("/import/commit")
def import_commit(payload: dict[str, object]) -> dict[str, object]:
    approval_manifest = Path(str(payload.get("approval_manifest") or ""))
    return LegacyRAGPipelineService().commit(approval_manifest).model_dump()


@router.get("/chunks")
def chunks() -> dict[str, object]:
    rows = LegacyRAGPipelineService().chunks()
    return {"status": "ok", "chunks": rows, "count": len(rows)}


@router.get("/chunks/{chunk_id}")
def chunk(chunk_id: str) -> dict[str, object]:
    row = LegacyRAGPipelineService().chunk(chunk_id)
    if row is None:
        raise HTTPException(status_code=404, detail="legacy_chunk_not_found")
    return {"status": "ok", "chunk": row}


@router.get("/conflicts")
def conflicts() -> dict[str, object]:
    rows = LegacyRAGPipelineService().conflicts()
    return {"status": "ok", "conflicts": rows, "count": len(rows)}


@router.get("/regression-candidates")
def regression_candidates() -> dict[str, object]:
    rows = LegacyRAGPipelineService().regression_candidates()
    return {"status": "ok", "regression_candidates": rows, "count": len(rows)}


@router.get("/lesson-candidates")
def lesson_candidates() -> dict[str, object]:
    rows = LegacyRAGPipelineService().lesson_candidates()
    return {"status": "ok", "lesson_candidates": rows, "count": len(rows)}
