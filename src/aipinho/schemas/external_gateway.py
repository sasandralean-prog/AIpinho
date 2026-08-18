from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


GatewayClientType = Literal["launcher", "cli", "vscode", "continue", "mcp", "rest", "web", "mobile", "future"]
GatewayStatus = Literal["accepted", "rejected", "blocked"]


class GatewayPolicy(AIpinhoModel):
    policy_id: str = Field(default_factory=lambda: f"gateway_policy_{uuid4().hex}")
    supported_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    allowed_client_types: list[GatewayClientType] = Field(default_factory=lambda: ["launcher", "cli", "vscode", "continue", "mcp", "rest", "web", "mobile", "future"])
    required_contract_keys: list[str] = Field(default_factory=lambda: ["contract_type"])
    forbidden_targets: list[str] = Field(
        default_factory=lambda: [
            "semantic_runtime",
            "governed_runtime",
            "runtime_doctor",
            "patch_intelligence",
            "semantic_learning",
            "cognitive_governance",
            "observability",
        ]
    )


class GatewayContext(AIpinhoModel):
    context_id: str = Field(default_factory=lambda: f"gateway_context_{uuid4().hex}")
    client_id: str
    client_type: GatewayClientType
    version: str
    source: str = "external"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewaySession(AIpinhoModel):
    gateway_session_id: str = Field(default_factory=lambda: f"gateway_session_{uuid4().hex}")
    client_id: str
    client_type: GatewayClientType
    version: str
    status: str = "active"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewaySessionRequest(AIpinhoModel):
    client_id: str
    client_type: GatewayClientType
    version: str = "1.0"
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewayRequest(AIpinhoModel):
    client_id: str
    client_type: GatewayClientType
    version: str = "1.0"
    session_id: str | None = None
    target_module: str
    contract: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewayResponse(AIpinhoModel):
    response_id: str = Field(default_factory=lambda: f"gateway_response_{uuid4().hex}")
    status: GatewayStatus
    gateway_session_id: str | None = None
    context: GatewayContext
    kernel_status: str = "not_dispatched"
    kernel_result: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    governed: bool = True
    internal_access_granted: bool = False
    deterministic: bool = True
    mutates_runtime: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GatewayHistory(AIpinhoModel):
    count: int
    responses: list[GatewayResponse] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False
