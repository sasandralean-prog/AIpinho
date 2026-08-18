from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.telemetry.runtime_metrics_service import RuntimeMetricsService


router = APIRouter(prefix="/api/v1/runtime", tags=["runtime-metrics"])


def _service() -> RuntimeMetricsService:
    return RuntimeMetricsService()


@router.get("/metrics")
def runtime_metrics() -> dict[str, object]:
    return _service().snapshot().model_dump(mode="json")


@router.get("/metrics/history")
def runtime_metrics_history() -> dict[str, object]:
    return _service().history().model_dump(mode="json")


@router.get("/health")
def runtime_health() -> dict[str, object]:
    return _service().health().model_dump(mode="json")
