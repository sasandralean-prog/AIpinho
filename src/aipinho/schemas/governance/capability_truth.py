from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class CapabilityTruthSnapshot(AIpinhoModel):
    can_create_preview: bool = True
    can_request_approval: bool = True
    can_execute_governed_tasks: bool = True
    can_read_workspace_when_allowed: bool = True
    can_write_workspace_when_allowed: bool = True
    can_run_shell_when_allowed: bool = True
    requires_policy: bool = True
    requires_approval_for_side_effects: bool = True
    limitations: list[str] = Field(default_factory=list)


class CapabilityAnswerPolicy(AIpinhoModel):
    answer_source: str = "CapabilityTruthService"
    raw_hidden_by_default: bool = True
    must_not_delegate_to_generic_llm: bool = True
