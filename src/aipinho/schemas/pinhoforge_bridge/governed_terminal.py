from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


TerminalBridgeStatus = Literal[
    "previewed",
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "timed_out",
    "cancelled",
    "running",
    "cancelling",
]


class PinhoForgeTerminalPreviewRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_terminal_preview_{uuid4().hex}")
    session_id: str | None = None
    command_source: str = "manual"
    command_id: str | None = None
    command_line: str | None = None
    cwd: str | None = None
    source_scope: str = "unknown"
    shell_category: str | None = None
    expected_outputs: list[str] = Field(default_factory=list)
    timeout_seconds: int = 60
    output_limit_kb: int = 64
    metadata: dict[str, Any] = Field(default_factory=dict)


class PinhoForgeTerminalPreviewResult(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    session_id: str
    status: TerminalBridgeStatus
    reason_code: str | None = None
    preview_id: str
    rendered_command: str | None = None
    cwd_redacted: str | None = None
    source_scope: str
    shell_category: str
    risk_level: str
    risk_score: int
    risk_reasons: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    autoapprove_eligible: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    execution_enabled: bool = False
    policy_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class PinhoForgeTerminalExecuteRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_terminal_execute_{uuid4().hex}")
    preview_id: str
    approval_id: str | None = None
    confirmed: bool = False
    timeout_seconds: int | None = None
    output_limit_kb: int | None = None
    expected_outputs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PinhoForgeTerminalExecuteResult(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    preview_id: str
    session_id: str
    execution_id: str
    status: TerminalBridgeStatus
    reason_code: str | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    duration_ms: int = 0
    output_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    report_markdown: str | None = None
    report_json: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    redaction_applied: bool = True


class PinhoForgeTerminalCancelRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_terminal_cancel_{uuid4().hex}")
    execution_id: str | None = None
    session_id: str | None = None


class PinhoForgeTerminalSessionStatus(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    session_id: str
    execution_id: str | None = None
    status: TerminalBridgeStatus
    reason_code: str | None = None
    cwd_redacted: str | None = None
    risk_level: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
