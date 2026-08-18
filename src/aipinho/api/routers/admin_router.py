from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/status")
def get_admin_status():
    return {"ok": True, "status": "not_implemented"}
