from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

DebuggerSeverity = Literal["info", "warning", "high", "critical"]
DebuggerStatusValue = Literal["ok", "missing", "degraded", "blocked", "failed"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DebuggerWarning(AIpinhoModel):
    code: str
    message: str
    severity: DebuggerSeverity = "warning"


class DebuggerBlockedReason(AIpinhoModel):
    code: str
    message: str
    severity: DebuggerSeverity = "critical"


class DebuggerSourceRef(AIpinhoModel):
    source_type: str = "unknown"
    source_id: str | None = None
    ref: str | None = None
    citation_id: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DebuggerSanitizationResult(AIpinhoModel):
    sanitized: bool = True
    redacted_fields: list[str] = Field(default_factory=list)
    truncated_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DebuggerTimelineEvent(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"debug_event_{uuid4().hex}")
    trace_id: str | None = None
    run_id: str | None = None
    event_type: str
    category: str = "debugger"
    status: str = "ok"
    summary: str = ""
    timestamp: str = Field(default_factory=utc_now)
    source_refs: list[DebuggerSourceRef] = Field(default_factory=list)
    warnings: list[DebuggerWarning] = Field(default_factory=list)
    blocked_reasons: list[DebuggerBlockedReason] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    sanitized: bool = True


class DebuggerTimeline(AIpinhoModel):
    timeline_id: str = Field(default_factory=lambda: f"debug_timeline_{uuid4().hex}")
    trace_id: str | None = None
    status: DebuggerStatusValue = "ok"
    events: list[DebuggerTimelineEvent] = Field(default_factory=list)
    warnings: list[DebuggerWarning] = Field(default_factory=list)
    blocked_reasons: list[DebuggerBlockedReason] = Field(default_factory=list)
    sanitized: bool = True


class DebuggerTrace(AIpinhoModel):
    trace_id: str
    status: DebuggerStatusValue = "ok"
    category: str = "debugger"
    events: list[DebuggerTimelineEvent] = Field(default_factory=list)
    sanitization: DebuggerSanitizationResult = Field(default_factory=DebuggerSanitizationResult)
    warnings: list[DebuggerWarning] = Field(default_factory=list)
    blocked_reasons: list[DebuggerBlockedReason] = Field(default_factory=list)


class DebuggerInspectionRequest(AIpinhoModel):
    target_type: str
    target_id: str
    include_trace: bool = True
    mode: Literal["sanitized", "explicit_internal_debug"] = "sanitized"


class DebuggerFinding(AIpinhoModel):
    finding_id: str = Field(default_factory=lambda: f"debug_finding_{uuid4().hex}")
    severity: DebuggerSeverity = "warning"
    code: str
    message: str
    source_refs: list[DebuggerSourceRef] = Field(default_factory=list)


class DebuggerInspectionResult(AIpinhoModel):
    inspection_id: str = Field(default_factory=lambda: f"debug_inspection_{uuid4().hex}")
    target_type: str
    target_id: str
    status: DebuggerStatusValue = "ok"
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    findings: list[DebuggerFinding] = Field(default_factory=list)
    timeline: DebuggerTimeline | None = None
    trace: DebuggerTrace | None = None
    sanitized: bool = True
    read_only: bool = True


class DebuggerStatus(AIpinhoModel):
    enabled: bool = True
    mode: str = "read_only_observability"
    sanitization_enabled: bool = True
    raw_prompt_visible_by_default: bool = False
    raw_output_visible_by_default: bool = False
    workspace_write_enabled: bool = False
    patch_apply_enabled: bool = False
    shell_enabled: bool = False
    git_enabled: bool = False
    memory_mutation_enabled: bool = False
    rag_ingestion_execute_enabled: bool = False
    approval_mutation_enabled: bool = False
    inspectors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class ModelRunInspection(DebuggerInspectionResult):
    target_type: str = "model_run"


class RoleRunInspection(DebuggerInspectionResult):
    target_type: str = "role_run"


class RAGRunInspection(DebuggerInspectionResult):
    target_type: str = "rag_run"


class RAGIngestionInspection(DebuggerInspectionResult):
    target_type: str = "rag_ingestion"


class ContextPlanInspection(DebuggerInspectionResult):
    target_type: str = "context_plan"


class MemoryUsageInspection(DebuggerInspectionResult):
    target_type: str = "memory_usage"


class VisionRunInspection(DebuggerInspectionResult):
    target_type: str = "vision_run"


class OCRRunInspection(DebuggerInspectionResult):
    target_type: str = "ocr_run"


class PatchApplyInspection(DebuggerInspectionResult):
    target_type: str = "patch_apply"


class ValidationInspection(DebuggerInspectionResult):
    target_type: str = "validation"


class OutputEvaluationInspection(DebuggerInspectionResult):
    target_type: str = "output_evaluation"
