from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


CodexGovernedActionType = Literal["create_file", "modify_file", "run_shell"]
CodexGovernedContractStatus = Literal[
    "preview",
    "approval_pending",
    "approved",
    "executing",
    "validating",
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "cancelled",
]


class CodexGovernedActionRequest(AIpinhoModel):
    action_type: CodexGovernedActionType
    target_path: str | None = None
    content: str | None = None
    argv: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = None
    expected_side_effects: list[str] = Field(default_factory=list)
    validation_required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> "CodexGovernedActionRequest":
        if self.action_type in {"create_file", "modify_file"}:
            if not self.target_path:
                raise ValueError("target_path_required")
            if self.content is None:
                raise ValueError("content_required")
            if self.argv:
                raise ValueError("argv_not_allowed_for_file_action")
        elif self.action_type == "run_shell":
            if not self.argv:
                raise ValueError("argv_required_for_shell_action")
            if self.target_path or self.content is not None:
                raise ValueError("file_payload_not_allowed_for_shell_action")
        return self


class CodexGovernedContractRequest(AIpinhoModel):
    session_id: str
    objective: str
    workspace_path: str
    actions: list[CodexGovernedActionRequest]
    run_id: str | None = None
    requested_by: str = "local_user"
    expires_in_minutes: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexGovernedProposalRequest(AIpinhoModel):
    session_id: str
    prompt: str
    workspace_path: str
    run_id: str | None = None
    model: str | None = None
    requested_by: str = "local_user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexGovernedAction(AIpinhoModel):
    action_id: str = Field(default_factory=lambda: f"codex_action_{uuid4().hex}")
    sequence: int
    action_type: CodexGovernedActionType
    workspace_path: str
    target_path: str | None = None
    content: str | None = None
    content_sha256: str | None = None
    original_sha256: str | None = None
    argv: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = None
    expected_side_effects: list[str] = Field(default_factory=list)
    validation_required: bool = True
    status: str = "preview"
    approval_id: str | None = None
    approval_status: str | None = None
    action_fingerprint: str
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexGovernedContract(AIpinhoModel):
    schema_version: int = 1
    contract_id: str = Field(default_factory=lambda: f"codex_contract_{uuid4().hex}")
    session_id: str
    run_id: str | None = None
    objective: str
    workspace_path: str
    workspace_id: str | None = None
    workspace_role: str | None = None
    status: CodexGovernedContractStatus = "preview"
    actions: list[CodexGovernedAction]
    contract_fingerprint: str
    approval_ids: list[str] = Field(default_factory=list)
    validation_status: str = "not_started"
    safe_to_execute: bool = False
    safe_to_report_success: bool = False
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    execution_summary: dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "local_user"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    expires_at: str


class CodexGovernedContractDecision(AIpinhoModel):
    status: str
    contract: CodexGovernedContract
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    message: str
