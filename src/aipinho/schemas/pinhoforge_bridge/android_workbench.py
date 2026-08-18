from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


AndroidWorkbenchStatus = Literal[
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "timeout",
]


class PinhoForgeAndroidWorkbenchRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_android_{uuid4().hex}")
    operation: Literal[
        "detect_project",
        "environment_readiness",
        "list_gradle_tasks",
        "execute_gradle_task",
        "adb_devices",
        "logcat_readonly",
        "export_report",
        "adb_shell",
        "adb_install",
        "adb_uninstall",
        "adb_push",
        "adb_pull",
        "clear_app_data",
    ]
    session_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    caller_agent_id: str | None = None
    workspace_ref: str | None = None
    project_path: str | None = None
    source_scope: str = "registered_workspace"
    task_id: str | None = None
    logcat_filter: str = ""
    timeout_seconds: int = 120
    output_limit_kb: int = 256
    metadata: dict[str, Any] = Field(default_factory=dict)


class PinhoForgeAndroidArtifact(AIpinhoModel):
    artifact_id: str | None = None
    filename: str
    content_type: str
    status: Literal["ready", "degraded", "blocked"] = "ready"
    requires_token: bool = True
    download_endpoint: str = "/api/v1/artifacts/{artifact_id}/download"


class PinhoForgeGradleExecutionResult(AIpinhoModel):
    task_id: str | None = None
    command_preview: list[str] = Field(default_factory=list)
    cwd_redacted: str | None = None
    status: Literal["completed", "completed_with_warnings", "failed", "blocked", "timeout", "cancelled"]
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    duration_ms: int | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PinhoForgeAndroidWorkbenchResult(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    operation: str
    status: AndroidWorkbenchStatus
    reason_code: str | None = None
    human_message: str
    project_profile: dict[str, Any] | None = None
    environment_readiness: dict[str, Any] | None = None
    gradle_tasks: list[dict[str, Any]] = Field(default_factory=list)
    command_preview: dict[str, Any] | None = None
    execution_result: PinhoForgeGradleExecutionResult | None = None
    adb_devices: list[dict[str, Any]] = Field(default_factory=list)
    logcat: dict[str, Any] | None = None
    report_markdown: str | None = None
    report_json: dict[str, Any] | None = None
    artifacts: list[PinhoForgeAndroidArtifact] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    redaction_applied: bool = True
    raw_hidden_by_default: bool = True

