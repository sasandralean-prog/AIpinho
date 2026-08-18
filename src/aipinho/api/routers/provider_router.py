from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


@router.get("")
def list_providers():
    return {"ok": True, "status": "not_implemented", "providers": []}
