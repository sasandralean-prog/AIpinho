from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RoleDefinition(AIpinhoModel):
    enabled: bool = True
    description: str = ""
    purpose: str = ""
    can_call_model: bool = False
    can_call_tools: bool = False
    can_execute_tools: bool = False
    can_write: bool = False
    can_patch: bool = False
    can_approve: bool = False
    allowed_purposes: list[str] = Field(default_factory=list)
    default_model_policy: str = "deterministic_only"
    output_contract: str = "plain_text"
    allowed_task_types: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    requires_approval: list[str] = Field(default_factory=list)


class RoleRegistryConfig(AIpinhoModel):
    schema_version: int
    roles: dict[str, RoleDefinition]
