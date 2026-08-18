from __future__ import annotations

from fastapi import APIRouter, Query

from aipinho.schemas.telemetry.dashboard import DashboardQuery
from aipinho.services.telemetry.runtime_dashboard_service import RuntimeDashboardService


router = APIRouter(prefix="/api/v1/runtime/dashboard", tags=["runtime-dashboard"])


def _service() -> RuntimeDashboardService:
    return RuntimeDashboardService()


@router.get("")
def runtime_dashboard() -> dict[str, object]:
    return _service().snapshot().model_dump(mode="json")


@router.get("/history")
def runtime_dashboard_history() -> dict[str, object]:
    return _service().history().model_dump(mode="json")


@router.get("/export")
def runtime_dashboard_export(format: str = Query(default="json", pattern="^(json|csv|markdown)$")) -> dict[str, object]:
    query = DashboardQuery(export_format=format)  # type: ignore[arg-type]
    return _service().export(query).model_dump(mode="json")
