from __future__ import annotations
from fastapi import APIRouter, Header, HTTPException
from starlette.responses import StreamingResponse
from aipinho.schemas.supervisor.contracts import ServiceRestartRequest
from aipinho.services.security.local_token_service import LocalTokenService
from aipinho.services.supervisor.supervisor_core import MonitorEventService, MonitorStatusBuilder, ResourceMonitorService, ServiceRestartService, SupervisorAuditService

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor-supervisor"])

def _require_token(authorization: str | None) -> None:
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="missing_or_invalid_bearer_token")

@router.get("/status")
def get_monitor_status() -> dict[str, object]:
    return {"status": "ok", "supervisor": MonitorStatusBuilder().status().model_dump()}

@router.get("/ports")
def get_ports() -> dict[str, object]:
    return {"status": "ok", "ports": [p.model_dump() for p in MonitorStatusBuilder().status().ports]}

@router.get("/services")
def get_services() -> dict[str, object]:
    return {"status": "ok", "services": [s.model_dump() for s in MonitorStatusBuilder().status().services]}

@router.get("/services/{service_id}")
def get_service(service_id: str) -> dict[str, object]:
    svc = next((s for s in MonitorStatusBuilder().status().services if s.service_id == service_id), None)
    return {"status": "ok" if svc else "missing", "service": svc.model_dump() if svc else None}

@router.get("/resources")
def get_resources() -> dict[str, object]:
    return {"status": "ok", "resources": ResourceMonitorService().snapshot().model_dump()}

@router.get("/human-health")
def get_human_health() -> dict[str, object]:
    st = MonitorStatusBuilder().status()
    return {"status": st.status, "human_summary": st.human_summary, "messages": [m.model_dump() for m in st.human_messages]}

@router.post("/services/{service_id}/restart")
def restart_service(service_id: str, request: ServiceRestartRequest | None = None, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    req = (request or ServiceRestartRequest(service_id=service_id)).model_copy(update={"service_id": service_id})
    result = ServiceRestartService().restart_service(req)
    return {"status": result.status, "restart": result.model_dump()}

@router.post("/ports/{port}/restart")
def restart_port(port: int, request: ServiceRestartRequest | None = None, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    req = (request or ServiceRestartRequest(port=port)).model_copy(update={"port": port})
    result = ServiceRestartService().restart_port(req)
    return {"status": result.status, "restart": result.model_dump()}

@router.get("/events")
def get_events() -> dict[str, object]:
    events = MonitorEventService().list_recent()
    return {"status": "ok", "events": events, "count": len(events)}

@router.get("/events/stream")
def stream_events():
    def gen():
        yield "event: service_status_changed\ndata: {\"status\":\"ok\"}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

@router.get("/audit")
def get_audit() -> dict[str, object]:
    audit = SupervisorAuditService().list_recent()
    return {"status": "ok", "audit": audit, "count": len(audit)}
