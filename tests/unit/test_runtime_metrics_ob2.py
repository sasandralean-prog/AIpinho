from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.runtime_metrics_router import router
from aipinho.schemas.telemetry.event import TelemetryRecordRequest
from aipinho.services.telemetry.runtime_metrics_service import MetricsAggregator, RuntimeMetricsService
from aipinho.services.telemetry.runtime_telemetry_service import RuntimeTelemetryService, TelemetryRepository


def _telemetry() -> RuntimeTelemetryService:
    return RuntimeTelemetryService(repository=TelemetryRepository())


def test_runtime_metrics_aggregates_counts_and_latency():
    telemetry = _telemetry()
    telemetry.record(
        TelemetryRecordRequest(
            category="routing",
            origin="cognitive",
            module="router",
            event_type="model_inference_scheduled",
            session_id="s1",
            task_run_id="r1",
            metadata={"duration_ms": 100, "role": "planner", "model": "local-reasoner"},
        )
    )
    telemetry.record(
        TelemetryRecordRequest(
            category="artifacts",
            origin="runtime",
            module="artifact_runtime",
            event_type="artifact_created",
            session_id="s1",
            task_run_id="r1",
            metadata={"duration_ms": 50, "role": "planner", "model": "local-reasoner"},
        )
    )
    snapshot = RuntimeMetricsService().snapshot()

    assert snapshot.event_count >= 2
    assert snapshot.task_run_count >= 1
    assert snapshot.artifact_count >= 1
    assert snapshot.inference_count >= 1
    assert snapshot.performance.average_latency_ms > 0
    assert snapshot.performance.time_by_role_ms["planner"] >= 150
    assert snapshot.performance.time_by_model_ms["local-reasoner"] >= 150
    assert snapshot.mutates_runtime is False


def test_runtime_metrics_history_is_reproducible_snapshot_list():
    service = RuntimeMetricsService()
    first = service.snapshot()
    second = service.snapshot()
    history = service.history()

    assert history.count >= 2
    assert first.snapshot_id != second.snapshot_id
    assert history.mutates_runtime is False


def test_runtime_health_degrades_when_error_events_exist():
    telemetry = _telemetry()
    telemetry.record(
        TelemetryRecordRequest(
            category="validation",
            origin="runtime",
            module="validation_service",
            event_type="validation_failed",
            severity="error",
            correlation_id="health_error",
        )
    )

    health = RuntimeMetricsService().health()

    assert health.status == "degraded"
    assert any(item.startswith("telemetry_error_events") for item in health.warnings)
    assert health.mutates_runtime is False


def test_metrics_aggregator_efficiency_indicators():
    telemetry = _telemetry()
    events = [
        telemetry.record(TelemetryRecordRequest(category="validation", origin="runtime", module="validation", event_type="validation_completed", session_id="s_eff", task_run_id="r_eff")),
        telemetry.record(TelemetryRecordRequest(category="escalation", origin="cognitive", module="escalation", event_type="escalation_evaluated", session_id="s_eff", task_run_id="r_eff")),
        telemetry.record(TelemetryRecordRequest(category="fire_test", origin="runtime", module="firetest", event_type="fire_test_completed", session_id="s_eff", task_run_id="r_eff")),
    ]
    snapshot = MetricsAggregator().snapshot(events)

    assert snapshot.validation_count >= 1
    assert snapshot.fire_test_count >= 1
    assert snapshot.escalation_count >= 1
    assert snapshot.efficiency.events_per_session >= 3


def test_runtime_metrics_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    metrics = client.get("/api/v1/runtime/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["mutates_runtime"] is False

    history = client.get("/api/v1/runtime/metrics/history")
    assert history.status_code == 200
    assert history.json()["count"] >= 1

    health = client.get("/api/v1/runtime/health")
    assert health.status_code == 200
    assert health.json()["mutates_runtime"] is False
