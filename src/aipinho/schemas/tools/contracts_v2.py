from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel

ToolProvider = str
ToolCapability = str
ToolRiskLevel = str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ToolContract(AIpinhoModel):
    tool_id: str
    provider: ToolProvider
    display_name: str
    capabilities: list[ToolCapability] = Field(default_factory=list)
    risk_level: ToolRiskLevel = "low"
    default_enabled: bool = False
    requires_approval: bool = False
    allowed_call_modes: list[str] = Field(default_factory=lambda: ["preview_only"])
    forbidden_call_modes: list[str] = Field(default_factory=lambda: ["direct_execution"])
    input_contract: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    sanitization_required: bool = True
    external_network: bool = False
    side_effect: bool = False
    availability: str = "disabled"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_boundaries(self) -> "ToolContract":
        if "direct_execution" in self.allowed_call_modes:
            raise ValueError("direct_execution_not_allowed")
        if self.risk_level in {"high", "critical"} and not self.requires_approval:
            raise ValueError("high_risk_tool_requires_approval")
        return self


class ToolRegistryEntry(AIpinhoModel):
    tool_id: str
    provider: str
    risk_level: str
    availability: str
    contract_valid: bool = True


class ToolAvailabilityStatus(AIpinhoModel):
    tool_id: str
    available: bool
    reason: str
    preview_only: bool = True


class ToolPermissionEnvelope(AIpinhoModel):
    envelope_id: str = Field(default_factory=lambda: f"tool_permission_{uuid4().hex}")
    skill_id: str
    allowed_tools: list[str] = Field(default_factory=list)
    denied_tools: list[str] = Field(default_factory=list)
    granted_capabilities: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)
    reasons: dict[str, str] = Field(default_factory=dict)
    direct_execution_allowed: bool = False


class ToolInvocationPreview(AIpinhoModel):
    invocation_preview_id: str = Field(default_factory=lambda: f"tool_invocation_preview_{uuid4().hex}")
    status: str
    tool_id: str
    skill_id: str | None = None
    call_mode: str = "preview_only"
    sanitized_input: dict[str, Any] = Field(default_factory=dict)
    blocked_reasons: list[str] = Field(default_factory=list)
    approval_required: bool = False
    executed: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class ToolInvocationResult(AIpinhoModel):
    status: str
    tool_id: str
    output: dict[str, Any] = Field(default_factory=dict)
    sanitized: bool = True
    executed: bool = False
