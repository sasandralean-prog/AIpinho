from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.telemetry.metric import MetricsSnapshot, RuntimeHealth


DashboardExportFormat = Literal["json", "csv", "markdown"]


class DashboardQuery(AIpinhoModel):
    include_history: bool = False
    export_format: DashboardExportFormat = "json"


class DashboardView(AIpinhoModel):
    name: str
    status: str = "ok"
    counters: dict[str, int | float] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardSnapshot(AIpinhoModel):
    dashboard_id: str = Field(default_factory=lambda: f"runtime_dashboard_{uuid4().hex}")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    runtime: DashboardView
    semantic_runtime: DashboardView
    governed_runtime: DashboardView
    runtime_doctor: DashboardView
    patch_intelligence: DashboardView
    semantic_learning: DashboardView
    cognitive_governance: DashboardView
    fire_tests: DashboardView
    metrics: MetricsSnapshot
    health: RuntimeHealth
    deterministic: bool = True
    mutates_runtime: bool = False


class DashboardHistory(AIpinhoModel):
    count: int
    snapshots: list[DashboardSnapshot] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False


class DashboardExport(AIpinhoModel):
    export_id: str = Field(default_factory=lambda: f"runtime_dashboard_export_{uuid4().hex}")
    format: DashboardExportFormat
    content_type: str
    content: str
    deterministic: bool = True
    mutates_runtime: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
