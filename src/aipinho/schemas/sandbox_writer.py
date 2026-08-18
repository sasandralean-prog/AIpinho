from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


SandboxWriteStatus = Literal["ready", "blocked", "failed"]


class SandboxWriteEvidence(AIpinhoModel):
    evidence_id: str
    kind: str
    status: str
    details: dict[str, object] = Field(default_factory=dict)


class SandboxWriteResult(AIpinhoModel):
    status: SandboxWriteStatus
    operation_type: str
    run_id: str
    path: str
    size_bytes: int = 0
    content_validated: bool = False
    policy_decision: str
    approval_decision: str
    evidence: list[SandboxWriteEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    reason_code: str | None = None

