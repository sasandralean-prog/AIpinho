from __future__ import annotations
from fastapi import APIRouter
from aipinho.services.mobile.mobile_status_service import MobileStatusService
router=APIRouter(prefix="/api/v1/mobile",tags=["mobile"])
@router.get("/status")
def mobile_status()->dict[str,object]: return MobileStatusService().status()
