from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("")
def create_task(payload: Dict[str, Any]):
    return {"ok": True, "status": "not_implemented", "task_id": None, "payload": payload}


@router.get("/{task_id}")
def get_task(task_id: str):
    return {"ok": True, "status": "not_implemented", "task_id": task_id}


@router.post("/{task_id}/run")
def run_task(task_id: str, payload: Dict[str, Any] | None = None):
    return {"ok": True, "status": "not_implemented", "task_id": task_id, "payload": payload or {}}


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, payload: Dict[str, Any] | None = None):
    return {"ok": True, "status": "not_implemented", "task_id": task_id, "payload": payload or {}}


@router.get("/{task_id}/events")
def get_task_events(task_id: str):
    return {"ok": True, "status": "not_implemented", "task_id": task_id, "events": []}


@router.get("/{task_id}/report")
def get_task_report(task_id: str):
    return {"ok": True, "status": "not_implemented", "task_id": task_id, "report": None}
