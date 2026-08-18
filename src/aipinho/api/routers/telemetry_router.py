from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.telemetry.event import TelemetryQuery, TelemetryRecordRequest
from aipinho.services.telemetry.runtime_telemetry_service import RuntimeTelemetryService


router = APIRouter(prefix="/api/v1/runtime/telemetry", tags=["runtime-telemetry"])
legacy_router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


def _service() -> RuntimeTelemetryService:
    return RuntimeTelemetryService()


@router.get("")
def get_runtime_telemetry(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, object]:
    return _service().list(limit=limit).model_dump(mode="json")


@router.post("/events")
def record_runtime_telemetry_event(request: TelemetryRecordRequest) -> dict[str, object]:
    return _service().record(request).model_dump(mode="json")


@router.get("/session/{session_id}")
def get_runtime_telemetry_session(session_id: str) -> dict[str, object]:
    session = _service().session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="telemetry_session_not_found")
    return session.model_dump(mode="json")


@router.post("/query")
def query_runtime_telemetry(query: TelemetryQuery) -> dict[str, object]:
    return _service().query(query).model_dump(mode="json")


@router.get("/status")
def runtime_telemetry_status() -> dict[str, object]:
    return _service().status()


@legacy_router.get("/events")
def get_legacy_telemetry_events(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, object]:
    return _service().list(limit=limit).model_dump(mode="json")
