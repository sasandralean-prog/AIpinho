from __future__ import annotations
import json, socket, time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen
from aipinho.core.paths import PATHS
from aipinho.schemas.supervisor.contracts import ServiceDefinition, ServiceManifest, ServiceHealth, PortStatus, ServiceStatus, ServiceRestartRequest, ServiceRestartResult, SupervisorAudit, SupervisorTrace, MonitorEvent
from aipinho.utils.yaml_loader import load_yaml_file

SERVICE_CONFIG = PATHS.config_root / "supervisor" / "service_manifest.yaml"
SUPERVISOR_DIR = PATHS.project_root / "data" / "runtime" / "supervisor"

def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

class ServiceManifestService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SERVICE_CONFIG
    def load_raw(self) -> dict[str, Any]:
        root = PATHS.project_root if self.path == SERVICE_CONFIG else self.path.parent
        return load_yaml_file(self.path, root=root)
    def load(self) -> ServiceManifest:
        raw = self.load_raw()
        services = {k: ServiceDefinition(**v) for k, v in (raw.get("services") or {}).items()}
        return ServiceManifest(schema_version=int(raw.get("schema_version", 1)), services=services, command_profiles=raw.get("command_profiles") or {}, rules=raw.get("rules") or {})
    def validate(self, manifest: ServiceManifest | None = None) -> dict[str, Any]:
        manifest = manifest or self.load()
        warnings: list[str] = []
        ports: dict[int, str] = {}
        forbidden_health_paths = {
            str(path).rstrip("/") or "/"
            for path in manifest.rules.get("forbidden_recursive_health_paths", [])
        }
        for sid, svc in manifest.services.items():
            if svc.port in ports:
                warnings.append(f"duplicate_port:{svc.port}:{ports[svc.port]}:{sid}")
            ports[svc.port] = sid
            if svc.command_profile not in manifest.command_profiles:
                warnings.append(f"missing_command_profile:{sid}:{svc.command_profile}")
            if svc.port == 9099 and svc.restartable:
                warnings.append("monitor_supervisor_must_not_be_restartable")
            health_path = urlparse(svc.health_url).path.rstrip("/") or "/"
            if health_path in forbidden_health_paths:
                warnings.append(f"recursive_health_url:{sid}:{health_path}")
        required_service_ids = {
            str(item)
            for item in manifest.rules.get("required_service_ids", [])
        }
        missing_required = sorted(required_service_ids - set(manifest.services))
        for service_id in missing_required:
            warnings.append(f"missing_required_service:{service_id}")
        return {"status": "ok" if not warnings else "degraded", "warnings": warnings, "service_count": len(manifest.services)}
    def status(self) -> dict[str, Any]:
        m = self.load(); v = self.validate(m)
        return {"status": v["status"], "service_count": len(m.services), "warnings": v["warnings"]}

class ServiceRegistryService:
    def __init__(self, manifest_service: ServiceManifestService | None = None) -> None:
        self.manifest_service = manifest_service or ServiceManifestService()
    def manifest(self) -> ServiceManifest:
        return self.manifest_service.load()
    def list_services(self) -> list[ServiceDefinition]:
        return list(self.manifest().services.values())
    def get(self, service_id: str) -> ServiceDefinition | None:
        return self.manifest().services.get(service_id)
    def by_port(self, port: int) -> ServiceDefinition | None:
        return next((s for s in self.list_services() if s.port == port), None)

class ServiceHealthChecker:
    def check(self, service: ServiceDefinition, timeout_seconds: float = 1.0) -> ServiceHealth:
        start = time.perf_counter()
        if service.health_url.startswith("mock://"):
            mode = service.health_url.removeprefix("mock://")
            if mode == "healthy":
                return ServiceHealth(service_id=service.service_id, status="healthy", http_status=200, latency_ms=1, human_message=f"{service.human_name or service.display_name} saudavel.")
            if mode == "degraded":
                return ServiceHealth(service_id=service.service_id, status="degraded", http_status=200, latency_ms=1500, human_message=f"{service.human_name or service.display_name} respondeu com atraso.")
            return ServiceHealth(service_id=service.service_id, status="down", error=mode or "mock_down", human_message=f"{service.human_name or service.display_name} fora do ar.")
        try:
            with urlopen(service.health_url, timeout=timeout_seconds) as response:
                latency = int((time.perf_counter() - start) * 1000)
                return ServiceHealth(service_id=service.service_id, status="healthy" if 200 <= response.status < 300 and latency < 1000 else "degraded", http_status=response.status, latency_ms=latency, human_message=f"{service.human_name or service.display_name} respondeu.")
        except Exception as exc:
            return ServiceHealth(service_id=service.service_id, status="down", latency_ms=int((time.perf_counter() - start) * 1000), error=str(exc), human_message=f"{service.human_name or service.display_name} fora do ar.")
    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "service_health_checker"}

class PortHealthService:
    def check_port(self, port: int, host: str = "127.0.0.1", service_id: str | None = None, managed_pid: int | None = None, timeout_seconds: float = 0.25) -> PortStatus:
        start = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout_seconds):
                status = "open" if service_id or managed_pid else "occupied_by_unknown"
                return PortStatus(port=port, host=host, service_id=service_id, status=status, managed_pid=managed_pid, latency_ms=int((time.perf_counter()-start)*1000), human_message="Porta aberta para servico registrado." if status == "open" else "Porta ocupada por processo desconhecido.")
        except OSError:
            return PortStatus(port=port, host=host, service_id=service_id, status="closed", latency_ms=int((time.perf_counter()-start)*1000), human_message="Porta fechada.")
    def list_manifest_ports(self) -> list[PortStatus]:
        return [self.check_port(s.port, host=s.host, service_id=s.service_id) for s in ServiceRegistryService().list_services()]
    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "port_health_service"}

class SupervisorAuditService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SUPERVISOR_DIR / "audit" / "audit.jsonl"
    def redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: ("[REDACTED_TOKEN]" if "token" in k.lower() or k.lower() == "authorization" else self.redact(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, str) and value.lower().startswith("bearer "):
            return "Bearer [REDACTED_TOKEN]"
        return value
    def record(self, audit: SupervisorAudit) -> SupervisorAudit:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = audit.model_dump(); payload["data"] = self.redact(payload.get("data", {}))
        with self.path.open("a", encoding="utf-8") as h: h.write(json.dumps(payload, ensure_ascii=True)+"\n")
        return SupervisorAudit(**payload)
    def list_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists(): return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()[-limit:] if line.strip()]

class SupervisorTraceService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SUPERVISOR_DIR / "traces"
    def record(self, trace: SupervisorTrace) -> SupervisorTrace:
        self.path.mkdir(parents=True, exist_ok=True); _write_json(self.path / f"{trace.trace_id}.json", trace.model_dump()); return trace

class MonitorEventService:
    def __init__(self, path: Path | None = None, audit: SupervisorAuditService | None = None) -> None:
        self.path = path or SUPERVISOR_DIR / "events" / "events.jsonl"; self.audit = audit or SupervisorAuditService()
    def record(self, event: MonitorEvent) -> MonitorEvent:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = event.model_dump(); payload["data"] = self.audit.redact(payload.get("data", {}))
        with self.path.open("a", encoding="utf-8") as h: h.write(json.dumps(payload, ensure_ascii=True)+"\n")
        return MonitorEvent(**payload)
    def list_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists(): return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()[-limit:] if line.strip()]

class ServiceRestartService:
    ALLOWED_PORTS = {9088, 9089, 9098}
    BLOCKED_PORTS = {9099}
    def __init__(self, registry: ServiceRegistryService | None = None, health: ServiceHealthChecker | None = None, audit: SupervisorAuditService | None = None, traces: SupervisorTraceService | None = None, events: MonitorEventService | None = None) -> None:
        self.registry = registry or ServiceRegistryService(); self.health = health or ServiceHealthChecker(); self.audit = audit or SupervisorAuditService(); self.traces = traces or SupervisorTraceService(); self.events = events or MonitorEventService(audit=self.audit)
    def restart_port(self, request: ServiceRestartRequest) -> ServiceRestartResult:
        if request.port is None: return self._blocked(request, None, "port_required")
        service = self.registry.by_port(request.port)
        if service is None: return self._blocked(request, None, "unknown_port")
        return self.restart_service(ServiceRestartRequest(service_id=service.service_id, port=service.port, requested_by=request.requested_by, device_id=request.device_id, reason=request.reason, command=request.command))
    def restart_service(self, request: ServiceRestartRequest) -> ServiceRestartResult:
        if request.command: return self._blocked(request, None, "arbitrary_command_blocked")
        if not request.service_id: return self._blocked(request, None, "service_id_required")
        service = self.registry.get(request.service_id)
        if service is None: return self._blocked(request, None, "unknown_service")
        if service.port in self.BLOCKED_PORTS or service.service_id == "monitor_supervisor": return self._blocked(request, service, "monitor_cannot_restart_itself")
        if service.port not in self.ALLOWED_PORTS: return self._blocked(request, service, "port_not_allowed")
        if not service.restartable: return self._blocked(request, service, "service_not_restartable")
        pre = self.health.check(service)
        trace = self.traces.record(SupervisorTrace(action="restart_service", service_id=service.service_id, port=service.port, status="accepted", events=[{"event":"pre_health","status":pre.status},{"event":"command_profile","profile":service.command_profile}]))
        audit = self.audit.record(SupervisorAudit(action="restart_service", service_id=service.service_id, port=service.port, requested_by=request.requested_by, device_id=request.device_id, status="accepted", data={"reason":request.reason,"command_profile":service.command_profile}))
        post = self.health.check(service)
        self.events.record(MonitorEvent(event_type="service_restarted", service_id=service.service_id, port=service.port, status="accepted", message=f"Restart controlado solicitado para {service.human_name or service.display_name}."))
        return ServiceRestartResult(service_id=service.service_id, port=service.port, status="accepted", allowed=True, pre_health=pre, post_health=post, audit_id=audit.audit_id, trace_id=trace.trace_id, warnings=[] if post.status == "healthy" else [f"post_health:{post.status}"], human_message=f"Reinicio controlado registrado para porta {service.port}.")
    def _blocked(self, request: ServiceRestartRequest, service: ServiceDefinition | None, reason: str) -> ServiceRestartResult:
        port = request.port if request.port is not None else (service.port if service else None); sid = request.service_id or (service.service_id if service else None)
        trace = self.traces.record(SupervisorTrace(action="restart_service", service_id=sid, port=port, status="blocked", events=[{"event":"blocked","reason":reason}]))
        audit = self.audit.record(SupervisorAudit(action="restart_service", service_id=sid, port=port, requested_by=request.requested_by, device_id=request.device_id, status="blocked", data={"reason":reason,"command":request.command,"authorization":"Bearer should-redact"}))
        self.events.record(MonitorEvent(event_type="service_restart_blocked", service_id=sid, port=port, status="blocked", message=reason, data={"authorization":"Bearer should-redact"}))
        return ServiceRestartResult(service_id=sid, port=port, status="blocked", allowed=False, audit_id=audit.audit_id, trace_id=trace.trace_id, blocked_reasons=[reason], human_message="Reinicio bloqueado por politica.")

from aipinho.schemas.supervisor.contracts import ResourceSnapshot, HumanHealthMessage, SupervisorStatus, LauncherStatus, ConnectionProfile, ConnectionTestRequest, ConnectionTestResult, ADBReverseStatus
from aipinho.services.security.local_token_service import LocalTokenService

class ResourceMonitorService:
    def snapshot(self) -> ResourceSnapshot:
        warnings: list[str] = []; cpu = ram = disk = None
        try:
            import psutil
            cpu=float(psutil.cpu_percent(interval=0.0)); ram=float(psutil.virtual_memory().percent); disk=float(psutil.disk_usage(str(PATHS.project_root)).percent)
        except Exception as exc:
            warnings.append(f"psutil_unavailable:{exc.__class__.__name__}")
            try:
                import shutil; u=shutil.disk_usage(PATHS.project_root); disk=round((u.used/u.total)*100,2)
            except Exception: warnings.append("disk_snapshot_unavailable")
        return ResourceSnapshot(cpu_percent=cpu, ram_percent=ram, disk_percent=disk, model_runtime_active=False, warnings=warnings)
    def status(self) -> dict[str, object]: return {"status":"ok","model_runtime_active":False}

class HumanHealthMessageService:
    def messages(self, services: list[ServiceStatus] | None = None) -> list[HumanHealthMessage]:
        services = services or MonitorStatusBuilder().service_statuses(); down=[s for s in services if s.status=="down"]; degraded=[s for s in services if s.status=="degraded"]
        out: list[HumanHealthMessage] = []
        if not down and not degraded: out.append(HumanHealthMessage(severity="healthy", message="Tudo saudavel. Backend, sincronizacao, arquivos e monitor estao ativos."))
        for s in down: out.append(HumanHealthMessage(severity="down", message=("Monitor supervisor fora do ar: somente o launcher pode reiniciar a porta 9099." if s.port==9099 else f"{s.human_message} Voce pode reiniciar a porta {s.port}."), service_id=s.service_id, port=s.port))
        for s in degraded: out.append(HumanHealthMessage(severity="degraded", message=s.human_message or f"Servico {s.service_id} degradado.", service_id=s.service_id, port=s.port))
        if any(s.port==9099 and not s.monitor_can_restart for s in services): out.append(HumanHealthMessage(severity="blocked", message="Reinicio bloqueado: a porta 9099 so pode ser reiniciada pelo launcher.", service_id="monitor_supervisor", port=9099))
        return out

class MonitorStatusBuilder:
    def __init__(self, registry: ServiceRegistryService | None = None, health: ServiceHealthChecker | None = None, ports: PortHealthService | None = None) -> None:
        self.registry=registry or ServiceRegistryService(); self.health=health or ServiceHealthChecker(); self.ports=ports or PortHealthService()
    def service_statuses(self) -> list[ServiceStatus]:
        items=[]
        for s in self.registry.list_services():
            h=self.health.check(s); can=s.restartable and s.port in ServiceRestartService.ALLOWED_PORTS and s.port not in ServiceRestartService.BLOCKED_PORTS
            items.append(ServiceStatus(service_id=s.service_id, display_name=s.display_name, port=s.port, health_url=s.health_url, status=h.status, restartable=s.restartable, monitor_can_restart=can, latency_ms=h.latency_ms, human_message=h.human_message, warnings=[] if can or s.port==9099 else ["not_restartable_by_monitor"]))
        return items
    def status(self) -> SupervisorStatus:
        services=self.service_statuses(); ports=[self.ports.check_port(s.port, host=s.host, service_id=s.service_id) for s in self.registry.list_services()]; msgs=HumanHealthMessageService().messages(services)
        status="healthy" if not any(s.status in {"down","degraded"} for s in services) else ("partial" if any(s.status=="down" for s in services) else "degraded")
        return SupervisorStatus(status=status, monitor_port=9099, monitor_exclusive=True, launcher_controls_monitor=True, token_configured=bool(LocalTokenService().status()["token_configured"]), services=services, ports=ports, resources=ResourceMonitorService().snapshot(), human_summary=msgs[0].message if msgs else "", human_messages=msgs)

class ConnectionProfileService:
    def __init__(self, path: Path | None = None, selected_path: Path | None = None) -> None:
        self.path=path or PATHS.config_root/"supervisor"/"connection_profiles.yaml"; self.selected_path=selected_path or SUPERVISOR_DIR/"selected_connection_profile.json"
    def list_profiles(self) -> list[ConnectionProfile]:
        raw=load_yaml_file(self.path, root=PATHS.project_root); out=[]
        for pid,data in (raw.get("profiles") or {}).items(): out.append(self.with_urls(ConnectionProfile(profile_id=pid, **data)))
        return out
    def get(self, profile_id: str) -> ConnectionProfile | None: return next((p for p in self.list_profiles() if p.profile_id==profile_id), None)
    def selected(self) -> str:
        if not self.selected_path.exists(): return "adb_reverse"
        return json.loads(self.selected_path.read_text(encoding="utf-8")).get("profile_id", "adb_reverse")
    def select(self, profile_id: str) -> ConnectionProfile:
        p=self.get(profile_id)
        if p is None: raise ValueError("unknown_connection_profile")
        _write_json(self.selected_path, {"profile_id":profile_id}); return p
    def with_urls(self, profile: ConnectionProfile, host: str | None = None) -> ConnectionProfile:
        selected_host=host or profile.host_for_mobile or ("127.0.0.1" if profile.profile_id=="adb_reverse" else "localhost")
        ports=profile.ports or {"bootstrap_control":9080,"core_backend":9088,"interaction_gateway":9089,"artifact_service":9098,"monitor_supervisor":9099}
        return profile.model_copy(update={"urls":{name:f"http://{selected_host}:{port}" for name,port in ports.items()}})

class ConnectionSuggestionService:
    DEFAULT_PORTS = {"bootstrap": 9080, "core_backend": 9088, "realtime": 9089, "artifacts": 9098, "monitor": 9099}
    PROFILE_PORT_KEYS = {"bootstrap_control": "bootstrap", "core_backend": "core_backend", "interaction_gateway": "realtime", "artifact_service": "artifacts", "monitor_supervisor": "monitor"}
    def __init__(self, profiles: ConnectionProfileService | None = None) -> None:
        self.profiles = profiles or ConnectionProfileService()
    def suggestions(self) -> dict[str, object]:
        default_ports = self._ports_for()
        return {
            "status": "ok",
            "ports": default_ports,
            "adb_reverse": self._adb_reverse(),
            "wifi_lan": self._profile_suggestion("wifi_lan", source="supervisor_profile"),
            "tailscale": self._profile_suggestion("tailscale", source="supervisor_profile"),
            "human_message": "Sugestoes de conexao calculadas sem scan agressivo de rede e sem expor token.",
        }
    def _ports_for(self, profile_id: str | None = None) -> dict[str, int]:
        profile = self.profiles.get(profile_id or "") if profile_id else None
        raw = profile.ports if profile and profile.ports else {"bootstrap_control": 9080, "core_backend": 9088, "interaction_gateway": 9089, "artifact_service": 9098, "monitor_supervisor": 9099}
        out = dict(self.DEFAULT_PORTS)
        for source, target in self.PROFILE_PORT_KEYS.items():
            if source in raw:
                out[target] = int(raw[source])
        return out
    def _adb_reverse(self) -> dict[str, object]:
        ports = self._ports_for("adb_reverse")
        commands = [f"adb reverse tcp:{port} tcp:{port}" for port in ports.values()]
        return {"host": "127.0.0.1", "detected": True, "source": "adb_reverse_profile", "ports": ports, "commands": commands}
    def _profile_suggestion(self, profile_id: str, *, source: str) -> dict[str, object]:
        profile = self.profiles.get(profile_id)
        host = profile.host_for_mobile if profile else None
        detected = bool(host)
        return {
            "host": host,
            "magic_dns": None if profile_id == "tailscale" else None,
            "detected": detected,
            "source": source if detected else "not_detected",
            "ports": self._ports_for(profile_id),
            "human_message": "Host sugerido pelo perfil configurado." if detected else "Nenhum host detectado; use pareamento, perfil salvo ou modo manual.",
        }

class ConnectionTestService:
    def test(self, request: ConnectionTestRequest) -> ConnectionTestResult:
        p=ConnectionProfileService().get(request.profile_id); ports=request.ports or (p.ports if p else {"bootstrap_control":9080,"core_backend":9088,"interaction_gateway":9089,"artifact_service":9098,"monitor_supervisor":9099}); host=request.host or (p.host_for_mobile if p and p.host_for_mobile else "127.0.0.1")
        results=[PortHealthService().check_port(port, host=host, service_id=name, timeout_seconds=request.timeout_seconds) for name,port in ports.items()]
        open_count=sum(1 for r in results if r.status=="open"); status="healthy" if open_count==len(results) else ("partial" if open_count else "down")
        return ConnectionTestResult(status=status, profile_id=request.profile_id, host=host, ports=results, human_message="Todas as portas responderam." if status=="healthy" else ("Algumas portas nao responderam." if status=="partial" else "Nenhuma porta respondeu."))

class ADBReverseService:
    PORTS=[9080,9088,9089,9098,9099]
    def commands(self) -> ADBReverseStatus: return ADBReverseStatus(commands=[f"adb reverse tcp:{p} tcp:{p}" for p in self.PORTS], ports=self.PORTS)
    def status(self) -> dict[str, object]: return {"status":"ok","auto_run_adb_allowed":False,"ports":self.PORTS}
class WifiLanProfileService:
    def status(self) -> dict[str, object]: return {"status":"ok","supported":True,"host_detection":"local_lan_ip"}
class TailscaleProfileService:
    def status(self) -> dict[str, object]: return {"status":"ok","supported":True,"host_detection":"manual_or_tailscale_ip"}
class MobilePairingService:
    def __init__(self, token_service: LocalTokenService | None = None) -> None: self.tokens=token_service or LocalTokenService()
    def status(self) -> dict[str, object]: return self.tokens.status()
    def create_token(self): return self.tokens.create_token(status="created")
    def rotate_token(self): return self.tokens.create_token(status="rotated")
    def verify(self, token: str | None, device_id: str | None = None):
        ok=self.tokens.validate_token(token); return {"status":"verified" if ok else "invalid","token_configured":self.tokens.status()["token_configured"],"device_id":device_id,"human_message":"Token valido." if ok else "Token invalido."}
class LauncherBootstrapService:
    def start_plan(self) -> LauncherStatus:
        services=ServiceRegistryService().list_services(); order=["monitor_supervisor"]+[s.service_id for s in services if s.service_id!="monitor_supervisor"]
        return LauncherStatus(status="ok", monitor_first=bool(order and order[0]=="monitor_supervisor"), planned_start_order=order)
    def bootstrap(self) -> dict[str, object]:
        token=LocalTokenService().ensure_token(); plan=self.start_plan(); return {"status":"ok","token_configured":True,"token_preview":token["token_preview"],"planned_start_order":plan.planned_start_order,"monitor_first":plan.monitor_first}
class LauncherWatchdogService:
    def status(self) -> dict[str, object]: return {"status":"ok","launcher_controls_monitor":True,"can_restart_monitor":True}
    def should_restart_monitor(self, monitor_health: ServiceHealth) -> bool: return monitor_health.status=="down"

