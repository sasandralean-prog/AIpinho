from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.runtime_dashboard_router import router
from aipinho.schemas.telemetry.dashboard import DashboardQuery
from aipinho.schemas.telemetry.event import TelemetryRecordRequest
from aipinho.services.telemetry.runtime_dashboard_service import RuntimeDashboardService
from aipinho.services.telemetry.runtime_telemetry_service import RuntimeTelemetryService, TelemetryRepository


def _seed_events() -> RuntimeTelemetryService:
    telemetry = RuntimeTelemetryService(repository=TelemetryRepository())
    telemetry.record(TelemetryRecordRequest(category="isr", origin="semantic_runtime", module="semantic_interpreter", event_type="isr_generated", session_id="s_dash", task_run_id="r_dash"))
    telemetry.record(TelemetryRecordRequest(category="contracts", origin="governed_runtime", module="contract_compiler", event_type="contract_created", session_id="s_dash", task_run_id="r_dash"))
    telemetry.record(TelemetryRecordRequest(category="validation", origin="runtime", module="validation", event_type="validation_completed", session_id="s_dash", task_run_id="r_dash"))
    telemetry.record(TelemetryRecordRequest(category="runtime_doctor", origin="doctor", module="runtime_doctor", event_type="regression_detected", severity="warning", session_id="s_dash", task_run_id="r_dash"))
    telemetry.record(TelemetryRecordRequest(category="escalation", origin="cognitive", module="cognitive_escalation", event_type="escalation_evaluated", session_id="s_dash", task_run_id="r_dash", metadata={"model": "local-reasoner"}))
    telemetry.record(TelemetryRecordRequest(category="fire_test", origin="runtime", module="firetest", event_type="fire_test_completed", session_id="s_dash", task_run_id="r_dash"))
    return telemetry


def test_runtime_dashboard_snapshot_consolidates_observability_sections():
    _seed_events()
    snapshot = RuntimeDashboardService().snapshot()

    assert snapshot.runtime.counters["events"] >= 6
    assert snapshot.semantic_runtime.counters["isr_generated"] >= 1
    assert snapshot.governed_runtime.counters["contracts"] >= 1
    assert snapshot.runtime_doctor.counters["regressions"] >= 1
    assert snapshot.cognitive_governance.counters["escalations"] >= 1
    assert snapshot.fire_tests.counters["history"] >= 1
    assert snapshot.mutates_runtime is False


def test_runtime_dashboard_history_keeps_snapshots():
    service = RuntimeDashboardService()
    first = service.snapshot()
    second = service.snapshot()
    history = service.history()

    assert history.count >= 2
    assert first.dashboard_id != second.dashboard_id
    assert history.mutates_runtime is False


def test_runtime_dashboard_exports_json_csv_and_markdown():
    _seed_events()
    service = RuntimeDashboardService()

    json_export = service.export(DashboardQuery(export_format="json"))
    csv_export = service.export(DashboardQuery(export_format="csv"))
    markdown_export = service.export(DashboardQuery(export_format="markdown"))

    assert json_export.content_type == "application/json"
    assert '"runtime"' in json_export.content
    assert csv_export.content_type == "text/csv"
    assert "section,status,counter,value" in csv_export.content
    assert markdown_export.content_type == "text/markdown"
    assert "# Runtime Dashboard" in markdown_export.content
    assert json_export.mutates_runtime is False


def test_runtime_dashboard_endpoint_views_and_exports():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    dashboard = client.get("/api/v1/runtime/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["mutates_runtime"] is False
    assert "runtime" in dashboard.json()

    history = client.get("/api/v1/runtime/dashboard/history")
    assert history.status_code == 200
    assert history.json()["count"] >= 1

    export = client.get("/api/v1/runtime/dashboard/export?format=markdown")
    assert export.status_code == 200
    assert export.json()["content_type"] == "text/markdown"


def test_runtime_dashboard_visualization_is_read_only_summary():
    _seed_events()
    snapshot = RuntimeDashboardService().snapshot()
    section_names = {
        snapshot.runtime.name,
        snapshot.semantic_runtime.name,
        snapshot.governed_runtime.name,
        snapshot.runtime_doctor.name,
        snapshot.patch_intelligence.name,
        snapshot.semantic_learning.name,
        snapshot.cognitive_governance.name,
        snapshot.fire_tests.name,
    }

    assert section_names == {
        "Runtime",
        "Semantic Runtime",
        "Governed Runtime",
        "Runtime Doctor",
        "Patch Intelligence",
        "Semantic Learning",
        "Cognitive Governance",
        "Fire Tests",
    }
    assert snapshot.deterministic is True
    assert snapshot.mutates_runtime is False
