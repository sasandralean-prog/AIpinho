from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.debugger.debug_trace_service import DebugTraceService

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])


@router.get("/traces/{trace_id}")
def get_debug_trace(trace_id: str) -> dict[str, object]:
    trace = DebugTraceService().get_trace(trace_id)
    return {"status": "ok" if trace.get("status") != "missing" else "missing", "trace": trace}


@router.get("/traces/{trace_id}/timeline")
def get_debug_trace_timeline(trace_id: str) -> dict[str, object]:
    return DebugTraceService().timeline(trace_id)
