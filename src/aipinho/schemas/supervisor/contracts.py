from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

ServiceRuntimeStatus = Literal["healthy", "degraded", "down", "blocked", "unknown", "restarting"]
RestartStatus = Literal["accepted", "blocked", "failed", "degraded"]

class ServiceDefinition(AIpinhoModel):
    service_id: str
    display_name: str
    port: int
    host: str = "127.0.0.1"
    public_bind_allowed: bool = False
    health_url: str
    start_mode: str = "managed_process"
    restartable: bool = False
    restartable_by_launcher_only: bool = False
    restart_group: str = "default"
    command_profile: str
    human_name: str = ""

class ServiceManifest(AIpinhoModel):
    schema_version: int = 1
    services: dict[str, ServiceDefinition] = Field(default_factory=dict)
    command_profiles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    rules: dict[str, Any] = Field(default_factory=dict)

class ServiceHealth(AIpinhoModel):
    service_id: str
    status: ServiceRuntimeStatus
    checked_at: str = Field(default_factory=utc_now)
    http_status: int | None = None
    latency_ms: int | None = None
    error: str | None = None
    human_message: str = ""

class PortStatus(AIpinhoModel):
    port: int
    host: str = "127.0.0.1"
    service_id: str | None = None
    status: Literal["open", "closed", "occupied_by_unknown", "unknown"] = "unknown"
    managed_pid: int | None = None
    latency_ms: int | None = None
    human_message: str = ""

class ServiceStatus(AIpinhoModel):
    service_id: str
    display_name: str
    port: int
    health_url: str
    status: ServiceRuntimeStatus
    restartable: bool
    monitor_can_restart: bool
    last_checked_at: str = Field(default_factory=utc_now)
    latency_ms: int | None = None
    human_message: str = ""
    warnings: list[str] = Field(default_factory=list)

class ServiceRestartRequest(AIpinhoModel):
    service_id: str | None = None
    port: int | None = None
    requested_by: str = "local_operator"
    device_id: str | None = None
    reason: str | None = None
    command: str | None = None

class ServiceRestartResult(AIpinhoModel):
    restart_id: str = Field(default_factory=lambda: f"restart_{uuid4().hex}")
    service_id: str | None = None
    port: int | None = None
    status: RestartStatus
    allowed: bool = False
    pre_health: ServiceHealth | None = None
    post_health: ServiceHealth | None = None
    audit_id: str | None = None
    trace_id: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    human_message: str = ""

BackendControlState = Literal["online", "offline", "restarting", "degraded", "unknown"]

class BackendControlStatus(AIpinhoModel):
    status: BackendControlState
    service_id: str = "core_backend"
    backend_port: int = 9088
    control_port: int = 9099
    exclusive_control_port: bool = True
    restart_endpoint: str = "/api/v1/backend-control/restart"
    health: ServiceHealth | None = None
    last_restart_id: str | None = None
    last_updated_at: str = Field(default_factory=utc_now)
    human_message: str = ""

class BackendControlRestartResult(AIpinhoModel):
    restart_id: str = Field(default_factory=lambda: f"backend_restart_{uuid4().hex}")
    status: Literal["accepted", "blocked", "failed", "degraded"]
    allowed: bool = False
    service_id: str = "core_backend"
    backend_port: int = 9088
    control_port: int = 9099
    pre_health: ServiceHealth | None = None
    post_health: ServiceHealth | None = None
    audit_id: str | None = None
    trace_id: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    human_message: str = ""

BootstrapControlState = Literal["online", "offline", "restarting", "degraded", "unknown"]

class BootstrapControlStatus(AIpinhoModel):
    status: BootstrapControlState
    service_id: str = "monitor_supervisor"
    bootstrap_port: int = 9080
    controlled_port: int = 9099
    restart_endpoint: str = "/api/v1/bootstrap-control/monitor/restart"
    health: ServiceHealth | None = None
    last_restart_id: str | None = None
    last_updated_at: str = Field(default_factory=utc_now)
    human_message: str = ""

class BootstrapControlRestartResult(AIpinhoModel):
    restart_id: str = Field(default_factory=lambda: f"bootstrap_restart_{uuid4().hex}")
    status: Literal["accepted", "blocked", "failed", "degraded"]
    allowed: bool = False
    service_id: str = "monitor_supervisor"
    bootstrap_port: int = 9080
    controlled_port: int = 9099
    pre_health: ServiceHealth | None = None
    post_health: ServiceHealth | None = None
    audit_id: str | None = None
    trace_id: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    human_message: str = ""

class ResourceSnapshot(AIpinhoModel):
    snapshot_id: str = Field(default_factory=lambda: f"resource_{uuid4().hex}")
    created_at: str = Field(default_factory=utc_now)
    cpu_percent: float | None = None
    ram_percent: float | None = None
    disk_percent: float | None = None
    model_runtime_active: bool = False
    warnings: list[str] = Field(default_factory=list)

class LauncherStatus(AIpinhoModel):
    status: str = "ok"
    monitor_first: bool = True
    launcher_controls_monitor: bool = True
    planned_start_order: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class ConnectionProfile(AIpinhoModel):
    profile_id: str
    display_name: str
    description: str = ""
    host_for_mobile: str | None = None
    host_detection: str | None = None
    ports: dict[str, int] = Field(default_factory=dict)
    ports_editable: bool = False
    commands_documentation: list[str] = Field(default_factory=list)
    auto_run_adb_allowed: bool | None = None
    urls: dict[str, str] = Field(default_factory=dict)

class ConnectionTestRequest(AIpinhoModel):
    profile_id: str = "manual"
    host: str | None = None
    ports: dict[str, int] | None = None
    timeout_seconds: float = 1.0

class ConnectionTestResult(AIpinhoModel):
    status: Literal["healthy", "partial", "down"]
    profile_id: str
    host: str
    ports: list[PortStatus] = Field(default_factory=list)
    human_message: str = ""

class MobilePairingRequest(AIpinhoModel):
    device_id: str | None = None
    device_name: str | None = None
    token: str | None = None

class MobilePairingResult(AIpinhoModel):
    status: Literal["created", "rotated", "verified", "invalid", "missing"]
    token_configured: bool
    token: str | None = None
    token_preview: str | None = None
    device_id: str | None = None
    human_message: str = ""

class MobilePairingToken(AIpinhoModel):
    token: str
    created_at: str = Field(default_factory=utc_now)
    expires_at: str | None = None
    token_preview: str

class PairedDevice(AIpinhoModel):
    device_id: str
    device_name: str | None = None
    paired_at: str = Field(default_factory=utc_now)
    last_seen_at: str | None = None

class ADBReverseStatus(AIpinhoModel):
    supported: bool = True
    auto_run_adb_allowed: bool = False
    commands: list[str] = Field(default_factory=list)
    ports: list[int] = Field(default_factory=list)

class HumanHealthMessage(AIpinhoModel):
    severity: Literal["healthy", "partial", "degraded", "down", "blocked"]
    message: str
    service_id: str | None = None
    port: int | None = None

class MonitorEvent(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"monitor_event_{uuid4().hex}")
    event_type: str
    service_id: str | None = None
    port: int | None = None
    status: str = "ok"
    message: str = ""
    created_at: str = Field(default_factory=utc_now)
    data: dict[str, Any] = Field(default_factory=dict)

class SupervisorAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"supervisor_audit_{uuid4().hex}")
    action: str
    service_id: str | None = None
    port: int | None = None
    requested_by: str = "local_operator"
    device_id: str | None = None
    status: str = "ok"
    created_at: str = Field(default_factory=utc_now)
    data: dict[str, Any] = Field(default_factory=dict)

class SupervisorTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: f"supervisor_trace_{uuid4().hex}")
    action: str
    service_id: str | None = None
    port: int | None = None
    status: str = "ok"
    created_at: str = Field(default_factory=utc_now)
    events: list[dict[str, Any]] = Field(default_factory=list)

class SupervisorStatus(AIpinhoModel):
    status: Literal["healthy", "partial", "degraded", "down"]
    monitor_port: int = 9099
    monitor_exclusive: bool = True
    launcher_controls_monitor: bool = True
    token_configured: bool = False
    services: list[ServiceStatus] = Field(default_factory=list)
    ports: list[PortStatus] = Field(default_factory=list)
    resources: ResourceSnapshot | None = None
    human_summary: str = ""
    human_messages: list[HumanHealthMessage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

