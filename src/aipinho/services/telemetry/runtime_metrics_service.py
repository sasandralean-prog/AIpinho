from __future__ import annotations

from aipinho.schemas.telemetry.event import TelemetryEvent
from aipinho.schemas.telemetry.metric import MetricsHistory, MetricsSnapshot, RuntimeEfficiency, RuntimeHealth, RuntimePerformance
from aipinho.services.telemetry.runtime_telemetry_service import TelemetryRepository


class MetricsCollector:
    def __init__(self, repository: TelemetryRepository | None = None) -> None:
        self.repository = repository or TelemetryRepository()

    def events(self) -> list[TelemetryEvent]:
        return self.repository.list()


class MetricsAggregator:
    def snapshot(self, events: list[TelemetryEvent]) -> MetricsSnapshot:
        task_run_ids = {event.task_run_id for event in events if event.task_run_id}
        session_ids = {event.session_id for event in events if event.session_id}
        durations = [float(event.metadata.get("duration_ms") or event.metadata.get("latency_ms") or 0) for event in events]
        positive_durations = [value for value in durations if value > 0]
        performance = RuntimePerformance(
            average_latency_ms=sum(positive_durations) / len(positive_durations) if positive_durations else 0.0,
            max_latency_ms=max(positive_durations) if positive_durations else 0.0,
            total_duration_ms=sum(positive_durations),
            time_by_role_ms=self._sum_by_metadata(events, "role"),
            time_by_model_ms=self._sum_by_metadata(events, "model"),
        )
        task_run_count = len(task_run_ids)
        session_count = len(session_ids)
        artifact_count = self._count_category(events, "artifacts")
        validation_count = self._count_category(events, "validation")
        escalation_count = self._count_category(events, "escalation")
        efficiency = RuntimeEfficiency(
            events_per_session=len(events) / session_count if session_count else 0.0,
            artifacts_per_task_run=artifact_count / task_run_count if task_run_count else 0.0,
            validations_per_task_run=validation_count / task_run_count if task_run_count else 0.0,
            escalations_per_task_run=escalation_count / task_run_count if task_run_count else 0.0,
        )
        health = self.health(events)
        return MetricsSnapshot(
            event_count=len(events),
            session_count=session_count,
            task_run_count=task_run_count,
            inference_count=self._count_event_type(events, "inference"),
            contract_count=self._count_category(events, "contracts"),
            artifact_count=artifact_count,
            validation_count=validation_count,
            fire_test_count=self._count_category(events, "fire_test"),
            regression_count=self._count_category_or_type(events, "regression"),
            patch_plan_count=self._count_category_or_type(events, "patch_plan"),
            semantic_recommendation_count=self._count_category_or_type(events, "semantic_recommendation"),
            escalation_count=escalation_count,
            approval_count=self._count_category_or_type(events, "approval"),
            performance=performance,
            efficiency=efficiency,
            health=health,
        )

    def health(self, events: list[TelemetryEvent]) -> RuntimeHealth:
        warnings: list[str] = []
        error_count = sum(1 for event in events if event.severity in {"error", "critical"})
        if error_count:
            warnings.append(f"telemetry_error_events:{error_count}")
        status = "degraded" if error_count else "ok"
        return RuntimeHealth(
            status=status,
            warnings=warnings,
            telemetry_events=len(events),
            active_signal_categories=sorted({event.category for event in events}),
        )

    def _count_category(self, events: list[TelemetryEvent], category: str) -> int:
        return sum(1 for event in events if event.category == category)

    def _count_event_type(self, events: list[TelemetryEvent], token: str) -> int:
        return sum(1 for event in events if token in event.event_type)

    def _count_category_or_type(self, events: list[TelemetryEvent], token: str) -> int:
        return sum(1 for event in events if token in event.category or token in event.event_type)

    def _sum_by_metadata(self, events: list[TelemetryEvent], key: str) -> dict[str, float]:
        totals: dict[str, float] = {}
        for event in events:
            label = event.metadata.get(key)
            if not label:
                continue
            duration = float(event.metadata.get("duration_ms") or event.metadata.get("latency_ms") or 0)
            totals[str(label)] = totals.get(str(label), 0.0) + duration
        return dict(sorted(totals.items()))


class RuntimeMetricsService:
    _history: list[MetricsSnapshot] = []

    def __init__(self, collector: MetricsCollector | None = None, aggregator: MetricsAggregator | None = None) -> None:
        self.collector = collector or MetricsCollector()
        self.aggregator = aggregator or MetricsAggregator()

    def snapshot(self) -> MetricsSnapshot:
        snapshot = self.aggregator.snapshot(self.collector.events())
        self._history.append(snapshot)
        return snapshot

    def history(self) -> MetricsHistory:
        return MetricsHistory(count=len(self._history), snapshots=list(self._history))

    def health(self) -> RuntimeHealth:
        return self.aggregator.health(self.collector.events())
