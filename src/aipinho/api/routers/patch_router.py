from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/patch", tags=["patch"])


@router.post("/preview")
def preview_patch(payload: Dict[str, Any]):
    return {"ok": True, "status": "not_implemented", "preview": None, "payload": payload}


@router.post("/apply")
def apply_patch(payload: Dict[str, Any]):
    return {"ok": True, "status": "not_implemented", "applied": False, "payload": payload}
