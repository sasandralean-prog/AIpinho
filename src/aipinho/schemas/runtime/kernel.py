from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


KernelState = Literal["INIT", "READY", "RUNNING", "WAITING_APPROVAL", "FAILED", "SHUTDOWN"]
KernelModuleStatus = Literal["registered", "ready", "blocked", "failed", "shutdown"]
KernelEventType = Literal["kernel_boot", "module_registered", "module_validated", "pipeline_traced", "kernel_failed", "kernel_shutdown"]
PipelineStageStatus = Literal["pending", "ready", "blocked", "completed"]


class KernelContext(AIpinhoModel):
    kernel_id: str = Field(default_factory=lambda: f"runtime_kernel_{uuid4().hex}")
    version: str = "1.0"
    state: KernelState = "INIT"
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class KernelModule(AIpinhoModel):
    module_id: str
    name: str
    version: str = "1.0"
    capabilities: list[str] = Field(default_factory=list)
    contracts: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    status: KernelModuleStatus = "registered"
    health: str = "unknown"
    can_read: bool = True
    can_write: bool = False
    can_execute: bool = False
    requires_contract: bool = True
    requires_validation: bool = True
    contracts_supported: list[str] = Field(default_factory=list)
    required_models: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KernelEvent(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"kernel_event_{uuid4().hex}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: KernelEventType
    kernel_id: str
    module_id: str | None = None
    status: str = "ok"
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KernelRegistry(AIpinhoModel):
    kernel_id: str
    modules: dict[str, KernelModule] = Field(default_factory=dict)
    events: list[KernelEvent] = Field(default_factory=list)


class KernelHealthReport(AIpinhoModel):
    kernel_id: str
    state: KernelState
    active_modules: list[str] = Field(default_factory=list)
    blocked_modules: list[str] = Field(default_factory=list)
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    boot_time_ms: float = 0.0
    status: str = "ok"
    warnings: list[str] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False


class ModuleContext(AIpinhoModel):
    kernel_id: str
    module_id: str
    state: KernelState
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModuleCapabilities(AIpinhoModel):
    can_read: bool = True
    can_write: bool = False
    can_execute: bool = False
    contracts_supported: list[str] = Field(default_factory=list)
    required_models: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)


class PipelineStage(AIpinhoModel):
    stage_id: str
    name: str
    input_contracts: list[str] = Field(default_factory=list)
    output_contracts: list[str] = Field(default_factory=list)
    evidence_required: bool = True
    rollback: str = "not_applicable"
    status: PipelineStageStatus = "pending"


class PipelineTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: f"pipeline_trace_{uuid4().hex}")
    kernel_id: str
    stages: list[PipelineStage] = Field(default_factory=list)
    skipped_stages: list[str] = Field(default_factory=list)
    complete: bool = False
    valid: bool = False
    warnings: list[str] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False


class KernelRuntimeReport(AIpinhoModel):
    kernel_id: str
    boot: str
    registry: str
    pipeline: str
    modules: str
    contracts: str
    validation: str
    health: KernelHealthReport
    coverage: dict[str, bool] = Field(default_factory=dict)
    verdict: str
    deterministic: bool = True
    mutates_runtime: bool = False
