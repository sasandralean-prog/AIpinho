from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RolePolicyRequest(AIpinhoModel):
    role_id: str
    intent_map: dict[str, object] = Field(default_factory=dict)
    policy_decision: dict[str, object] = Field(default_factory=dict)
    task_contract: dict[str, object] = Field(default_factory=dict)
    approval_state: dict[str, object] = Field(default_factory=dict)
    pipeline_context: dict[str, object] = Field(default_factory=dict)
