from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.debugger.multi_island_trace import TraceExportRequest
from aipinho.services.debugger.debugger_status_service import DebuggerStatusService
from aipinho.services.debugger.debugger_timeline_builder import DebuggerTimelineBuilder
from aipinho.services.debugger.debugger_trace_service_v2 import DebuggerTraceServiceV2
from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService
from aipinho.services.debugger.multi_island_trace_service import MultiIslandTraceService

router = APIRouter(prefix="/api/v1/debugger", tags=["debugger-v2"])


@router.get("/status")
def get_debugger_status() -> dict[str, object]:
    return DebuggerStatusService().status()


@router.get("/traces")
def list_multi_island_traces(limit: int = 50) -> dict[str, object]:
    traces = MultiIslandTraceService().recent(limit=limit)
    return {"status": "ok", "traces": [trace.model_dump() for trace in traces], "raw_default_visible": False}


@router.get("/traces/{trace_id}")
def get_trace(trace_id: str) -> dict[str, object]:
    observability = MultiAgentObservabilityService()
    if observability.sessions.get_run(trace_id) is not None:
        graph = observability.trace_graph(trace_id)
        return {"status": "ok", "trace_graph": graph.model_dump(), "raw_default_visible": False}
    trace = DebuggerTraceServiceV2().get(trace_id)
    body = trace.model_dump()
    return {"status": trace.status, "warnings": body.get("warnings", []), "blocked_reasons": body.get("blocked_reasons", []), "trace": body}


@router.get("/by-bridge-task/{bridge_task_id}")
def get_trace_by_bridge_task(bridge_task_id: str) -> dict[str, object]:
    trace = MultiIslandTraceService().by_bridge_task(bridge_task_id)
    return {"status": "ok", "trace": trace.model_dump(), "raw_default_visible": False}


@router.get("/by-task/{task_id}")
def get_trace_by_task(task_id: str) -> dict[str, object]:
    trace = MultiIslandTraceService().by_run(task_id)
    return {"status": "ok", "trace": trace.model_dump(), "raw_default_visible": False}


@router.get("/by-agent/{agent_id}")
def get_traces_by_agent(agent_id: str, limit: int = 50) -> dict[str, object]:
    traces = MultiIslandTraceService().by_agent(agent_id, limit=limit)
    return {"status": "ok", "agent_id": agent_id, "traces": [trace.model_dump() for trace in traces], "raw_default_visible": False}


@router.get("/by-artifact/{artifact_id}")
def get_trace_by_artifact(artifact_id: str) -> dict[str, object]:
    trace = MultiIslandTraceService().by_artifact(artifact_id)
    return {"status": "ok", "trace": trace.model_dump(), "raw_default_visible": False}


@router.get("/recent")
def get_recent_traces(limit: int = 50) -> dict[str, object]:
    traces = MultiIslandTraceService().recent(limit=limit)
    return {"status": "ok", "traces": [trace.model_dump() for trace in traces], "raw_default_visible": False}


@router.post("/traces/{trace_id}/export")
def export_trace(trace_id: str, request: TraceExportRequest) -> dict[str, object]:
    result = MultiIslandTraceService().export(trace_id, request)
    return {"status": "ok" if result.status in {"READY", "READY_WITH_WARNINGS"} else "blocked", "result": result.model_dump()}


@router.get("/traces/{trace_id}/timeline")
def get_timeline(trace_id: str) -> dict[str, object]:
    timeline = DebuggerTimelineBuilder().build(trace_id)
    body = timeline.model_dump()
    return {"status": timeline.status, "warnings": body.get("warnings", []), "blocked_reasons": body.get("blocked_reasons", []), "timeline": body}


@router.post("/traces/resolve")
def resolve_trace(payload: dict[str, object]) -> dict[str, object]:
    return DebuggerTraceServiceV2().resolve(payload)
