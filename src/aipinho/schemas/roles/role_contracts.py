from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


RoleLifecycleStatus = Literal["enabled", "disabled"]


class RoleCapability(AIpinhoModel):
    capability_id: str
    description: str = ""
    source: str = "role_contract"


class RolePermission(AIpinhoModel):
    can_call_llm: bool = False
    can_call_tools: bool = False
    can_execute_tools: bool = False
    can_write: bool = False
    can_patch: bool = False
    can_approve: bool = False
    tools_allowed: list[str] = Field(default_factory=list)
    skills_allowed: list[str] = Field(default_factory=list)
    output_types_allowed: list[str] = Field(default_factory=list)
    requires_approval: list[str] = Field(default_factory=list)


class RoleRestriction(AIpinhoModel):
    forbidden_actions: list[str] = Field(default_factory=list)
    tools_forced_off: bool = True
    writes_forced_off: bool = True
    patches_forced_off: bool = True
    runtime_execution_forbidden: bool = True


class RoleLifecycle(AIpinhoModel):
    status: RoleLifecycleStatus = "enabled"
    source_config: str = "config/roles/default_roles.yaml"
    loaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RoleExecutionPolicy(AIpinhoModel):
    model_policy: str = "deterministic_only"
    side_effects_allowed: bool = False
    approval_required_for_side_effects: bool = True
    allowed_purposes: list[str] = Field(default_factory=list)


class RoleContract(AIpinhoModel):
    role_id: str
    version: str = "1.0"
    description: str = ""
    purpose: str = ""
    capabilities: list[RoleCapability] = Field(default_factory=list)
    permissions: RolePermission = Field(default_factory=RolePermission)
    restrictions: RoleRestriction = Field(default_factory=RoleRestriction)
    lifecycle: RoleLifecycle = Field(default_factory=RoleLifecycle)
    execution_policy: RoleExecutionPolicy = Field(default_factory=RoleExecutionPolicy)
    metadata: dict[str, Any] = Field(default_factory=dict)
