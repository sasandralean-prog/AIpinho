from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RuntimePerformance(AIpinhoModel):
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    total_duration_ms: float = 0.0
    time_by_role_ms: dict[str, float] = Field(default_factory=dict)
    time_by_model_ms: dict[str, float] = Field(default_factory=dict)


class RuntimeEfficiency(AIpinhoModel):
    events_per_session: float = 0.0
    artifacts_per_task_run: float = 0.0
    validations_per_task_run: float = 0.0
    escalations_per_task_run: float = 0.0


class RuntimeHealth(AIpinhoModel):
    status: str = "ok"
    warnings: list[str] = Field(default_factory=list)
    telemetry_events: int = 0
    active_signal_categories: list[str] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MetricsSnapshot(AIpinhoModel):
    snapshot_id: str = Field(default_factory=lambda: f"metrics_snapshot_{uuid4().hex}")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_count: int = 0
    session_count: int = 0
    task_run_count: int = 0
    inference_count: int = 0
    contract_count: int = 0
    artifact_count: int = 0
    validation_count: int = 0
    fire_test_count: int = 0
    regression_count: int = 0
    patch_plan_count: int = 0
    semantic_recommendation_count: int = 0
    escalation_count: int = 0
    approval_count: int = 0
    performance: RuntimePerformance = Field(default_factory=RuntimePerformance)
    efficiency: RuntimeEfficiency = Field(default_factory=RuntimeEfficiency)
    health: RuntimeHealth = Field(default_factory=RuntimeHealth)
    metadata: dict[str, Any] = Field(default_factory=dict)
    deterministic: bool = True
    mutates_runtime: bool = False


class MetricsHistory(AIpinhoModel):
    count: int
    snapshots: list[MetricsSnapshot] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False
