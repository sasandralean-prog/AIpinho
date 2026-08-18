from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


CapabilitySelectionStatus = Literal["primary", "fallback", "escalation", "disabled", "unavailable", "blocked", "requested"]


class CapabilityContract(AIpinhoModel):
    capability_id: str
    display_name: str
    enabled: bool = True
    aliases: list[str] = Field(default_factory=list)
    required_model_capabilities: list[str] = Field(default_factory=list)
    primary_model: str | None = None
    fallback_models: list[str] = Field(default_factory=list)
    escalation_models: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityModelBinding(AIpinhoModel):
    binding_id: str
    capability_id: str
    role_id: str | None = None
    enabled: bool = True
    primary_model: str | None = None
    fallback_models: list[str] = Field(default_factory=list)
    escalation_models: list[str] = Field(default_factory=list)
    output_contract: str | None = None
    allowed_model_capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilitySelection(AIpinhoModel):
    allowed: bool = False
    status: CapabilitySelectionStatus = "blocked"
    capability_id: str | None = None
    role_id: str | None = None
    selected_model_id: str | None = None
    provider_id: str | None = None
    fallback_model_id: str | None = None
    selection_source: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
