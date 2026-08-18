from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


GovernedWriteOperation = Literal["create_file", "modify_file", "create_directory"]


class GovernedWriteRequest(AIpinhoModel):
    """Canonical chat-to-tool-gateway write request.

    The request describes user intent and workspace resolution metadata; the
    Tool Gateway remains responsible for policy, approval, execution and
    validation.
    """

    operation_type: GovernedWriteOperation
    session_id: str
    prompt: str
    workspace_ref: str | None = None
    filename: str | None = None
    content_hint: str = ""
    requested_capabilities: list[str] = Field(default_factory=list)
    execution_mode: str = "governed_autorun"
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class GovernedWriteOutcome(AIpinhoModel):
    status: str
    reason_code: str | None = None
    workspace_ref: str | None = None
    workspace_id: str | None = None
    workspace_role: str | None = None
    resolved_path_sanitized: str | None = None
    run_id: str | None = None
    draft_id: str | None = None
    preview_id: str | None = None
    approval_id: str | None = None
    tool_invocation_id: str | None = None
    policy_decision_id: str | None = None
    validation_status: str | None = None
    file_path_sanitized: str | None = None
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
