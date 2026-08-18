from __future__ import annotations

import json
import time
from typing import Any

from aipinho import __version__
from aipinho.schemas.telemetry.dashboard import DashboardExport, DashboardHistory, DashboardQuery, DashboardSnapshot, DashboardView
from aipinho.schemas.telemetry.event import TelemetryEvent
from aipinho.services.telemetry.runtime_metrics_service import RuntimeMetricsService
from aipinho.services.telemetry.runtime_telemetry_service import TelemetryRepository


class RuntimeDashboardService:
    _history: list[DashboardSnapshot] = []
    _started_at = time.monotonic()

    def __init__(self, repository: TelemetryRepository | None = None, metrics: RuntimeMetricsService | None = None) -> None:
        self.repository = repository or TelemetryRepository()
        self.metrics = metrics or RuntimeMetricsService()

    def snapshot(self, query: DashboardQuery | None = None) -> DashboardSnapshot:
        events = self.repository.list()
        metrics = self.metrics.snapshot()
        snapshot = DashboardSnapshot(
            runtime=self._runtime_view(events),
            semantic_runtime=self._semantic_view(events),
            governed_runtime=self._governed_view(events),
            runtime_doctor=self._doctor_view(events),
            patch_intelligence=self._patch_view(events),
            semantic_learning=self._learning_view(events),
            cognitive_governance=self._cognitive_view(events),
            fire_tests=self._firetest_view(events),
            metrics=metrics,
            health=metrics.health,
        )
        self._history.append(snapshot)
        return snapshot

    def history(self) -> DashboardHistory:
        return DashboardHistory(count=len(self._history), snapshots=list(self._history))

    def export(self, query: DashboardQuery) -> DashboardExport:
        snapshot = self.snapshot(query)
        if query.export_format == "csv":
            return DashboardExport(format="csv", content_type="text/csv", content=self._csv(snapshot))
        if query.export_format == "markdown":
            return DashboardExport(format="markdown", content_type="text/markdown", content=self._markdown(snapshot))
        return DashboardExport(format="json", content_type="application/json", content=json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True))

    def _runtime_view(self, events: list[TelemetryEvent]) -> DashboardView:
        active_sessions = {event.session_id for event in events if event.session_id}
        return DashboardView(
            name="Runtime",
            status="ok",
            counters={"events": len(events), "active_sessions": len(active_sessions), "uptime_seconds": round(time.monotonic() - self._started_at, 3)},
            highlights=[f"version:{__version__}", "read_only_dashboard"],
            metadata={"session_ids": sorted(active_sessions)[-10:]},
        )

    def _semantic_view(self, events: list[TelemetryEvent]) -> DashboardView:
        return DashboardView(
            name="Semantic Runtime",
            counters={
                "isr_generated": self._count(events, category="isr"),
                "concepts_learned": self._count(events, event_token="semantic_concept"),
                "competencies": self._count(events, event_token="semantic_competency"),
            },
        )

    def _governed_view(self, events: list[TelemetryEvent]) -> DashboardView:
        return DashboardView(
            name="Governed Runtime",
            counters={
                "contracts": self._count(events, category="contracts"),
                "approvals": self._count(events, event_token="approval"),
                "validations": self._count(events, category="validation"),
            },
        )

    def _doctor_view(self, events: list[TelemetryEvent]) -> DashboardView:
        warnings = [event.event_type for event in events if event.category == "runtime_doctor" and event.severity in {"warning", "error", "critical"}]
        return DashboardView(
            name="Runtime Doctor",
            status="degraded" if warnings else "ok",
            counters={"regressions": self._count(events, event_token="regression"), "doctor_events": self._count(events, category="runtime_doctor")},
            warnings=warnings[-10:],
        )

    def _patch_view(self, events: list[TelemetryEvent]) -> DashboardView:
        return DashboardView(
            name="Patch Intelligence",
            counters={
                "proposals": self._count(events, event_token="patch_proposal"),
                "patterns": self._count(events, event_token="patch_pattern"),
                "knowledge": self._count(events, event_token="patch_knowledge"),
            },
        )

    def _learning_view(self, events: list[TelemetryEvent]) -> DashboardView:
        return DashboardView(
            name="Semantic Learning",
            counters={
                "curriculum": self._count(events, event_token="semantic_curriculum"),
                "recommendations": self._count(events, event_token="semantic_recommendation"),
                "competencies": self._count(events, event_token="semantic_competency"),
            },
        )

    def _cognitive_view(self, events: list[TelemetryEvent]) -> DashboardView:
        models = sorted({str(event.metadata.get("model")) for event in events if event.metadata.get("model")})
        return DashboardView(
            name="Cognitive Governance",
            counters={
                "models_used": len(models),
                "decisions": self._count(events, category="governance"),
                "escalations": self._count(events, category="escalation"),
            },
            metadata={"models": models},
        )

    def _firetest_view(self, events: list[TelemetryEvent]) -> DashboardView:
        failures = [event for event in events if event.category == "fire_test" and event.severity in {"error", "critical"}]
        successes = [event for event in events if event.category == "fire_test" and ("passed" in event.event_type or event.event_type.endswith("completed"))]
        return DashboardView(
            name="Fire Tests",
            status="degraded" if failures else "ok",
            counters={"history": self._count(events, category="fire_test"), "success": len(successes), "failures": len(failures)},
            highlights=["trend:stable" if not failures else "trend:needs_review"],
        )

    def _count(self, events: list[TelemetryEvent], category: str | None = None, event_token: str | None = None) -> int:
        return sum(1 for event in events if (category is None or event.category == category) and (event_token is None or event_token in event.event_type))

    def _csv(self, snapshot: DashboardSnapshot) -> str:
        rows = ["section,status,counter,value"]
        for view in self._views(snapshot):
            if not view.counters:
                rows.append(f"{view.name},{view.status},,")
            for key, value in view.counters.items():
                rows.append(f"{view.name},{view.status},{key},{value}")
        return "\n".join(rows)

    def _markdown(self, snapshot: DashboardSnapshot) -> str:
        lines = [f"# Runtime Dashboard", "", f"Snapshot: `{snapshot.dashboard_id}`", f"Health: `{snapshot.health.status}`", ""]
        for view in self._views(snapshot):
            lines.extend([f"## {view.name}", f"Status: `{view.status}`", ""])
            for key, value in view.counters.items():
                lines.append(f"- `{key}`: {value}")
            if view.warnings:
                lines.append(f"- `warnings`: {', '.join(view.warnings)}")
            lines.append("")
        return "\n".join(lines).strip()

    def _views(self, snapshot: DashboardSnapshot) -> list[DashboardView]:
        return [
            snapshot.runtime,
            snapshot.semantic_runtime,
            snapshot.governed_runtime,
            snapshot.runtime_doctor,
            snapshot.patch_intelligence,
            snapshot.semantic_learning,
            snapshot.cognitive_governance,
            snapshot.fire_tests,
        ]
