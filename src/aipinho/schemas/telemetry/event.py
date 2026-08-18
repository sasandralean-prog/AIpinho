from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


TelemetryCategory = Literal[
    "task",
    "task_run",
    "session",
    "intent",
    "isr",
    "contracts",
    "roles",
    "model_selection",
    "routing",
    "escalation",
    "runtime_doctor",
    "fire_test",
    "artifacts",
    "validation",
    "completion",
    "speaker_truth",
    "governance",
]
TelemetrySeverity = Literal["debug", "info", "warning", "error", "critical"]


class TelemetryEvent(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"telemetry_event_{uuid4().hex}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    category: TelemetryCategory
    origin: str
    module: str
    event_type: str
    severity: TelemetrySeverity = "info"
    correlation_id: str
    session_id: str | None = None
    task_run_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    deterministic: bool = True
    mutates_runtime: bool = False


class TelemetrySession(AIpinhoModel):
    telemetry_session_id: str = Field(default_factory=lambda: f"telemetry_session_{uuid4().hex}")
    correlation_id: str
    session_id: str | None = None
    task_run_id: str | None = None
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_count: int = 0
    categories: list[TelemetryCategory] = Field(default_factory=list)


class TelemetryRecordRequest(AIpinhoModel):
    category: TelemetryCategory
    origin: str
    module: str
    event_type: str
    severity: TelemetrySeverity = "info"
    correlation_id: str | None = None
    session_id: str | None = None
    task_run_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetryQuery(AIpinhoModel):
    category: TelemetryCategory | None = None
    origin: str | None = None
    module: str | None = None
    event_type: str | None = None
    severity: TelemetrySeverity | None = None
    correlation_id: str | None = None
    session_id: str | None = None
    task_run_id: str | None = None
    limit: int = 100


class TelemetryEventList(AIpinhoModel):
    count: int
    events: list[TelemetryEvent] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False


class TelemetrySessionView(AIpinhoModel):
    session: TelemetrySession
    events: list[TelemetryEvent] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False
