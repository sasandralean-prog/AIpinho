from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


BridgeOperation = Literal["handshake", "health", "manifest", "readiness", "execute"]
BridgeStatus = Literal["ok", "blocked", "unauthorized", "timeout", "unsupported", "failed", "invalid_manifest"]


class PinhoForgeBridgeCapability(AIpinhoModel):
    capability_id: str
    display_name: str
    category: str
    risk_level: str = "unknown"
    status: str = "unknown"
    experimental: bool = False
    supports_dry_run: bool = False
    supports_batch: bool = False
    supports_artifacts: bool = False
    requires_external_tool: bool = False
    required_tools: list[str] = Field(default_factory=list)
    execution_enabled: bool = False
    limitations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class PinhoForgeBridgeModule(AIpinhoModel):
    module_id: str
    category: str
    capability_count: int = 0
    status: str = "unknown"
    execution_enabled: bool = False
    notes: list[str] = Field(default_factory=list)


class PinhoForgeBridgeManifest(AIpinhoModel):
    schema_version: int
    provider_id: str
    generated_at: str
    app_name: str
    bridge_mode: str
    execution_enabled: bool = False
    modules: list[PinhoForgeBridgeModule] = Field(default_factory=list)
    capabilities: list[PinhoForgeBridgeCapability] = Field(default_factory=list)
    external_tools: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class PinhoForgeProviderStatus(AIpinhoModel):
    provider_id: str = "pinhoforge_studio"
    status: str
    mode: str = "discovery_only"
    execution_enabled: bool = False
    manifest_loaded: bool = False
    manifest_path_sanitized: str | None = None
    capability_count: int = 0
    module_count: int = 0
    allowed_operations: list[str] = Field(default_factory=list)
    blocked_operations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=utc_now_iso)


class PinhoForgeBridgePolicyDecision(AIpinhoModel):
    policy_decision_id: str = Field(default_factory=lambda: f"pinhoforge_policy_{uuid4().hex}")
    operation: str
    decision: Literal["allow", "deny"]
    reason_code: str
    human_reason: str
    execution_enabled: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class PinhoForgeBridgeRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_request_{uuid4().hex}")
    operation: BridgeOperation
    payload: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 30


class PinhoForgeBridgeResponse(AIpinhoModel):
    request_id: str
    trace_id: str = Field(default_factory=lambda: f"pinhoforge_trace_{uuid4().hex}")
    provider_id: str = "pinhoforge_studio"
    operation: str
    status: BridgeStatus
    execution_enabled: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)
    policy_decision: PinhoForgeBridgePolicyDecision | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    raw_hidden_by_default: bool = True
    created_at: str = Field(default_factory=utc_now_iso)
