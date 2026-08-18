from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.interaction.interaction_core import TaskSyncService

router = APIRouter(prefix="/api/v1/tasks", tags=["task-sync"])


@router.get("/cards")
def task_cards() -> dict[str, object]:
    return {"status": "ok", "cards": [card.model_dump() for card in TaskSyncService().list_cards()]}


@router.get("/{task_id}/timeline")
def task_timeline(task_id: str) -> dict[str, object]:
    return {"status": "ok", "task_id": task_id, "timeline": TaskSyncService().timeline(task_id)}
