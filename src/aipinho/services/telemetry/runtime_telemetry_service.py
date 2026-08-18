from __future__ import annotations

from datetime import datetime, timezone

from aipinho.schemas.telemetry.event import (
    TelemetryEvent,
    TelemetryEventList,
    TelemetryQuery,
    TelemetryRecordRequest,
    TelemetrySession,
    TelemetrySessionView,
)


class TelemetryRepository:
    _events: list[TelemetryEvent] = []
    _sessions: dict[str, TelemetrySession] = {}

    def add(self, event: TelemetryEvent) -> TelemetryEvent:
        self._events.append(event)
        self._update_session(event)
        return event

    def list(self) -> list[TelemetryEvent]:
        return list(self._events)

    def query(self, query: TelemetryQuery) -> list[TelemetryEvent]:
        rows = self._events
        filters = {
            "category": query.category,
            "origin": query.origin,
            "module": query.module,
            "event_type": query.event_type,
            "severity": query.severity,
            "correlation_id": query.correlation_id,
            "session_id": query.session_id,
            "task_run_id": query.task_run_id,
        }
        for field, expected in filters.items():
            if expected is not None:
                rows = [event for event in rows if getattr(event, field) == expected]
        return rows[-query.limit :]

    def session(self, session_id: str) -> TelemetrySessionView | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        events = [event for event in self._events if event.session_id == session_id or event.correlation_id == session.correlation_id]
        categories = sorted({event.category for event in events})
        session = session.model_copy(
            update={
                "event_count": len(events),
                "categories": categories,
                "updated_at": events[-1].timestamp if events else session.updated_at,
            }
        )
        return TelemetrySessionView(session=session, events=events)

    def _update_session(self, event: TelemetryEvent) -> None:
        key = event.session_id or event.correlation_id
        existing = self._sessions.get(key)
        categories = sorted({*(existing.categories if existing else []), event.category})
        if existing is None:
            self._sessions[key] = TelemetrySession(
                correlation_id=event.correlation_id,
                session_id=event.session_id,
                task_run_id=event.task_run_id,
                event_count=1,
                categories=categories,
            )
            return
        self._sessions[key] = existing.model_copy(
            update={
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "event_count": existing.event_count + 1,
                "categories": categories,
                "task_run_id": existing.task_run_id or event.task_run_id,
            }
        )


class TelemetryCollector:
    def collect(self, request: TelemetryRecordRequest) -> TelemetryEvent:
        correlation_id = request.correlation_id or request.task_run_id or request.session_id or request.task_id or "runtime_unscoped"
        return TelemetryEvent(
            category=request.category,
            origin=request.origin,
            module=request.module,
            event_type=request.event_type,
            severity=request.severity,
            correlation_id=correlation_id,
            session_id=request.session_id,
            task_run_id=request.task_run_id,
            task_id=request.task_id,
            metadata=request.metadata,
        )


class TelemetrySerializer:
    def event(self, event: TelemetryEvent) -> dict[str, object]:
        return event.model_dump(mode="json")

    def event_list(self, events: list[TelemetryEvent]) -> dict[str, object]:
        return TelemetryEventList(count=len(events), events=events).model_dump(mode="json")


class RuntimeTelemetryService:
    def __init__(self, repository: TelemetryRepository | None = None, collector: TelemetryCollector | None = None) -> None:
        self.repository = repository or TelemetryRepository()
        self.collector = collector or TelemetryCollector()

    def record(self, request: TelemetryRecordRequest) -> TelemetryEvent:
        return self.repository.add(self.collector.collect(request))

    def list(self, limit: int = 100) -> TelemetryEventList:
        events = self.repository.list()[-limit:]
        return TelemetryEventList(count=len(events), events=events)

    def query(self, query: TelemetryQuery) -> TelemetryEventList:
        events = self.repository.query(query)
        return TelemetryEventList(count=len(events), events=events)

    def session(self, session_id: str) -> TelemetrySessionView | None:
        return self.repository.session(session_id)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "runtime_telemetry",
            "events": len(self.repository.list()),
            "deterministic": True,
            "mutates_runtime": False,
        }
