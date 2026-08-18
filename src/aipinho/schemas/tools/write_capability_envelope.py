from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


WriteOperationType = Literal[
    "create_file",
    "modify_file",
    "delete_file",
    "create_directory",
    "move_file",
    "apply_patch",
    "run_shell_write",
    "run_shell_test",
    "run_shell_build",
    "run_shell_readonly",
]

WriteEnvelopeStatus = Literal["created", "valid", "blocked", "approval_required"]


class WriteCapabilityEnvelope(AIpinhoModel):
    operation_id: str = Field(default_factory=lambda: f"write_op_{uuid4().hex}")
    task_id: str | None = None
    session_id: str | None = None
    workspace_id: str
    workspace_role: str
    target_path: str | None = None
    operation_type: WriteOperationType
    capability_required: str
    policy_decision_id: str | None = None
    approval_id: str | None = None
    preview_id: str | None = None
    expected_side_effects: list[str] = Field(default_factory=list)
    risk_score: str = "medium"
    actor: str = "system"
    created_at: str
    status: WriteEnvelopeStatus = "created"
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, object]] = Field(default_factory=list)


class WriteCapabilityEnvelopeDecision(AIpinhoModel):
    allowed: bool
    envelope: WriteCapabilityEnvelope
    reason: str
