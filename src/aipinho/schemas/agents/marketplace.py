from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.session.session_store import utc_now


AgentTrustLevel = Literal["L0", "L1", "L2", "L3", "L4"]
AgentHealthStatus = Literal["online", "offline", "degraded", "unhealthy", "disabled"]
AgentLifecycleStatus = Literal["registered", "active", "disabled", "removed"]


class AgentCapabilityDescriptor(AIpinhoModel):
    capability_id: str
    version: str = "1.0"
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    cost_weight: int = 1
    latency_weight: int = 1


class AgentScope(AIpinhoModel):
    workspace_scope: list[str] = Field(default_factory=list)
    capability_scope: list[str] = Field(default_factory=list)
    filesystem_scope: list[str] = Field(default_factory=list)
    execution_scope: list[str] = Field(default_factory=list)
    network_scope: list[str] = Field(default_factory=list)


class AgentManifest(AIpinhoModel):
    agent_id: str
    name: str
    version: str = "1.0.0"
    manifest_version: str = "1"
    api_version: str = "1"
    contract_version: str = "1"
    capability_version: str = "1"
    capabilities: list[AgentCapabilityDescriptor] = Field(default_factory=list)
    trust_level: AgentTrustLevel = "L1"
    runtime_profile: str = "supervised"
    health_endpoint: str | None = None
    heartbeat_interval_seconds: int = 30
    cost: int = 1
    latency_ms: int = 1000
    priority: int = 50
    restrictions: list[str] = Field(default_factory=list)
    scope: AgentScope = Field(default_factory=AgentScope)
    lifecycle_status: AgentLifecycleStatus = "registered"
    health_status: AgentHealthStatus = "online"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentHeartbeat(AIpinhoModel):
    heartbeat_id: str = Field(default_factory=lambda: f"agent_heartbeat_{uuid4().hex}")
    agent_id: str
    status: AgentHealthStatus = "online"
    cpu_percent: float | None = None
    ram_mb: float | None = None
    queue_depth: int | None = None
    average_latency_ms: int | None = None
    errors: int = 0
    available: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class AgentHealthSnapshot(AIpinhoModel):
    agent_id: str
    health_status: AgentHealthStatus
    last_heartbeat_at: str | None = None
    consecutive_failures: int = 0
    total_failures: int = 0
    auto_disabled: bool = False
    average_latency_ms: int | None = None
    queue_depth: int | None = None
    updated_at: str = Field(default_factory=utc_now)


class CapabilityMatch(AIpinhoModel):
    agent_id: str
    agent_name: str
    capability_id: str
    trust_level: AgentTrustLevel
    health_status: AgentHealthStatus
    runtime_profile: str
    score: float
    cost: int
    latency_ms: int
    priority: int
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CapabilityQuery(AIpinhoModel):
    capability_id: str
    workspace: str | None = None
    required_trust_level: AgentTrustLevel | None = None
    include_unhealthy: bool = False


class CapabilityNegotiationResult(AIpinhoModel):
    query: CapabilityQuery
    selected: CapabilityMatch | None = None
    candidates: list[CapabilityMatch] = Field(default_factory=list)
    status: Literal["matched", "no_match", "blocked"] = "no_match"
    reason_code: str | None = None


class AgentMarketplaceSnapshot(AIpinhoModel):
    status: Literal["ok", "degraded"] = "ok"
    agents: list[AgentManifest] = Field(default_factory=list)
    health: list[AgentHealthSnapshot] = Field(default_factory=list)
    capabilities: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
