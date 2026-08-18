from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

RolePassMode = Literal["preview", "run"]


class RolePassInput(AIpinhoModel):
    pass_id: str = "single_pass"
    role_id: str
    required: bool = True
    user_message: str = ""
    purpose: str = "chat"
    intent_map: dict[str, object] = Field(default_factory=dict)
    policy_decision: dict[str, object] = Field(default_factory=dict)
    task_contract: dict[str, object] = Field(default_factory=dict)
    project_report: dict[str, object] = Field(default_factory=dict)
    file_context_bundle: dict[str, object] = Field(default_factory=dict)
    context_injection_plan_id: str | None = None
    context_injection_plan: dict[str, object] = Field(default_factory=dict)
    evidence: list[dict[str, object]] = Field(default_factory=list)
    session_id: str | None = None
    mode: RolePassMode = "run"
    model_mode: str = "stub"
    requested_model_id: str | None = None
    allow_real_inference: bool = False
    operator_confirmed: bool = False
    include_trace: bool = False
