from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.telemetry_router import legacy_router, router
from aipinho.schemas.telemetry.event import TelemetryQuery, TelemetryRecordRequest
from aipinho.services.telemetry.runtime_telemetry_service import RuntimeTelemetryService, TelemetryRepository


def _service() -> RuntimeTelemetryService:
    return RuntimeTelemetryService(repository=TelemetryRepository())


def test_runtime_telemetry_records_correlatable_event_without_runtime_mutation():
    service = _service()
    event = service.record(
        TelemetryRecordRequest(
            category="task_run",
            origin="runtime",
            module="task_runtime_service",
            event_type="task_run_started",
            correlation_id="corr_1",
            session_id="session_1",
            task_run_id="run_1",
            task_id="task_1",
            metadata={"phase": "running"},
        )
    )

    assert event.event_id.startswith("telemetry_event_")
    assert event.correlation_id == "corr_1"
    assert event.session_id == "session_1"
    assert event.task_run_id == "run_1"
    assert event.mutates_runtime is False
    scoped = service.query(TelemetryQuery(correlation_id="corr_1"))
    assert any(item.event_id == event.event_id for item in scoped.events)


def test_telemetry_session_groups_events_by_session_and_correlation():
    service = _service()
    service.record(TelemetryRecordRequest(category="session", origin="chat", module="chat_service", event_type="session_started", correlation_id="corr_2", session_id="session_2"))
    service.record(TelemetryRecordRequest(category="routing", origin="cognitive", module="cognitive_router", event_type="route_resolved", correlation_id="corr_2"))

    view = service.session("session_2")

    assert view is not None
    assert view.session.event_count == 2
    assert {event.category for event in view.events} == {"session", "routing"}


def test_telemetry_query_filters_by_category_and_task_run():
    service = _service()
    service.record(TelemetryRecordRequest(category="artifacts", origin="runtime", module="artifact_runtime", event_type="artifact_created", task_run_id="run_3"))
    service.record(TelemetryRecordRequest(category="validation", origin="runtime", module="validation_service", event_type="validation_completed", task_run_id="run_3"))
    service.record(TelemetryRecordRequest(category="validation", origin="runtime", module="validation_service", event_type="validation_completed", task_run_id="run_4"))

    result = service.query(TelemetryQuery(category="validation", task_run_id="run_3"))

    assert result.count == 1
    assert result.events[0].task_run_id == "run_3"
    assert result.events[0].category == "validation"


def test_telemetry_serialization_is_structured_and_deterministic():
    service = _service()
    event = service.record(TelemetryRecordRequest(category="speaker_truth", origin="runtime", module="runtime_truth_engine", event_type="truth_evaluated"))
    body = event.model_dump(mode="json")

    assert body["category"] == "speaker_truth"
    assert body["deterministic"] is True
    assert body["mutates_runtime"] is False


def test_runtime_telemetry_endpoints_and_legacy_events_endpoint():
    app = FastAPI()
    app.include_router(router)
    app.include_router(legacy_router)
    client = TestClient(app)

    recorded = client.post(
        "/api/v1/runtime/telemetry/events",
        json={
            "category": "escalation",
            "origin": "cognitive_governance",
            "module": "cognitive_escalation_engine",
            "event_type": "escalation_evaluated",
            "correlation_id": "corr_endpoint",
            "session_id": "session_endpoint",
            "task_run_id": "run_endpoint",
        },
    )
    assert recorded.status_code == 200
    assert recorded.json()["mutates_runtime"] is False

    listed = client.get("/api/v1/runtime/telemetry")
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    session = client.get("/api/v1/runtime/telemetry/session/session_endpoint")
    assert session.status_code == 200
    assert session.json()["session"]["session_id"] == "session_endpoint"

    queried = client.post("/api/v1/runtime/telemetry/query", json={"correlation_id": "corr_endpoint"})
    assert queried.status_code == 200
    assert queried.json()["count"] >= 1

    legacy = client.get("/api/v1/telemetry/events")
    assert legacy.status_code == 200
    assert legacy.json()["count"] >= 1
