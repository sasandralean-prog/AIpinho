from __future__ import annotations
from fastapi import APIRouter
from aipinho.services.ux.ux_health_service import UXHealthService
from aipinho.services.ux.ux_notification_service import UXNotificationService
from aipinho.services.ux.ux_session_recovery_service import UXSessionRecoveryService
from aipinho.services.ux.ux_status_service import UXStatusService
router=APIRouter(prefix="/api/v1",tags=["ux"])
@router.get("/ux/status")
def ux_status()->dict[str,object]: return UXStatusService().status().model_dump()
@router.get("/ux/health")
def ux_health()->dict[str,object]: return UXHealthService().health().model_dump()
@router.get("/ux/notifications")
def ux_notifications()->dict[str,object]: return {"status":"ok","notifications":[i.model_dump() for i in UXNotificationService().list()]}
@router.post("/ux/notifications/ack")
def ux_notifications_ack(payload:dict[str,object])->dict[str,object]:
    ids=payload.get("notification_ids",[]); items=UXNotificationService().ack([str(i) for i in ids] if isinstance(ids,list) else [])
    return {"status":"ok","notifications":[i.model_dump() for i in items]}
@router.get("/session/recovery")
def session_recovery()->dict[str,object]: return UXSessionRecoveryService().get().model_dump()
@router.post("/session/recovery/restore")
def restore_session_recovery(payload:dict[str,object])->dict[str,object]: return UXSessionRecoveryService().restore(payload).model_dump()
