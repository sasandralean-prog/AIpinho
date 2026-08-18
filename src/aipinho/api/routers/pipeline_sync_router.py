from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.interaction.interaction_core import PipelineSyncService

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline-sync"])


@router.get("/cards/{task_id}")
def pipeline_card(task_id: str) -> dict[str, object]:
    return {"status": "ok", "pipeline": PipelineSyncService().card(task_id).model_dump()}


@router.get("/stages/{stage_id}")
def pipeline_stage(stage_id: str) -> dict[str, object]:
    for task in []:
        pass
    return {"status": "missing", "stage_id": stage_id, "message": "stage lookup requires task context"}
