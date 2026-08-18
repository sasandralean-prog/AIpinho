from pathlib import Path
import json
from fastapi import APIRouter, HTTPException
from aipinho.core.paths import PATHS
from aipinho.schemas.maintenance.contracts import MaintenanceLessonCandidateRequest
from aipinho.services.maintenance.maintenance_core import MaintenanceLessonCandidateService

router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance-signals"])

@router.get("/signals")
def signals() -> dict[str, object]:
    root = PATHS.project_root / "data" / "runtime" / "maintenance" / "signals"
    items = []
    if root.exists():
        for path in sorted(root.glob("*.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
    return {"status": "ok", "signals": items}

@router.get("/lessons/candidates")
def lesson_candidates() -> dict[str, object]:
    items = MaintenanceLessonCandidateService().list()
    return {"status": "ok", "count": len(items), "candidates": [item.model_dump() for item in items]}

@router.post("/lessons/candidates")
def create_lesson_candidate(request: MaintenanceLessonCandidateRequest) -> dict[str, object]:
    try:
        item = MaintenanceLessonCandidateService().create(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "ok", "candidate": item.model_dump()}
