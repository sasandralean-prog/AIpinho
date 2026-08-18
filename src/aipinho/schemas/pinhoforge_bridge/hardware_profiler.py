from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


HardwareProfilerStatus = Literal[
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "timeout",
]


class PinhoForgeHardwareProfilerRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_hardware_{uuid4().hex}")
    operation: Literal[
        "get_environment_profile",
        "get_tool_availability",
        "get_readiness_summary",
        "export_environment_report",
        "install_tool",
        "repair_environment",
        "modify_path",
        "run_diagnostic_command_arbitrary",
        "execute_terminal",
        "run_build",
    ]
    session_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    caller_agent_id: str | None = None
    include_tools: bool = True
    include_hardware: bool = True
    include_android: bool = True
    include_media: bool = True
    include_development: bool = True
    redaction_required: bool = True
    timeout_seconds: int = 30
    force_refresh: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PinhoForgeToolAvailabilityItem(AIpinhoModel):
    tool_id: str
    display_name: str
    status: Literal["available", "missing", "error", "unknown"]
    version: str | None = None
    executable_path_redacted: str | None = None
    used_by_capabilities: list[str] = Field(default_factory=list)
    readiness_impact: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PinhoForgeReadinessSummary(AIpinhoModel):
    conversion_readiness: Literal["ready", "partial", "missing", "degraded", "unknown", "error"]
    android_readiness: Literal["ready", "partial", "missing", "degraded", "unknown", "error"]
    media_readiness: Literal["ready", "partial", "missing", "degraded", "unknown", "error"]
    development_readiness: Literal["ready", "partial", "missing", "degraded", "unknown", "error"]
    terminal_readiness: Literal["ready", "partial", "missing", "degraded", "unknown", "error"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class PinhoForgeHardwareProfilerResult(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    operation: str
    status: HardwareProfilerStatus
    reason_code: str | None = None
    human_message: str
    generated_at: str | None = None
    system_profile: dict[str, Any] | None = None
    hardware_profile: dict[str, Any] | None = None
    tool_availability: list[PinhoForgeToolAvailabilityItem] = Field(default_factory=list)
    readiness_summary: PinhoForgeReadinessSummary | None = None
    report_markdown: str | None = None
    report_json: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    redaction_applied: bool = True
    evidence_refs: list[str] = Field(default_factory=list)
    raw_hidden_by_default: bool = True

