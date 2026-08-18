from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.supervisor.contracts import (
    BootstrapControlRestartResult,
    BootstrapControlStatus,
    MonitorEvent,
    ServiceHealth,
    SupervisorAudit,
    SupervisorTrace,
)
from aipinho.services.supervisor.supervisor_core import (
    MonitorEventService,
    ServiceHealthChecker,
    ServiceRegistryService,
    SupervisorAuditService,
    SupervisorTraceService,
)
from aipinho.utils.yaml_loader import load_yaml_file


class BootstrapControlService:
    """Tiny out-of-band control plane for the monitor supervisor.

    This service intentionally starts/restarts only the configured monitor
    supervisor through canonical scripts. It never accepts arbitrary commands.
    """

    def __init__(
        self,
        policy_path: Path | None = None,
        registry: ServiceRegistryService | None = None,
        health: ServiceHealthChecker | None = None,
        audit: SupervisorAuditService | None = None,
        traces: SupervisorTraceService | None = None,
        events: MonitorEventService | None = None,
        runner=subprocess.run,
    ) -> None:
        self.policy_path = policy_path or PATHS.config_root / "supervisor" / "bootstrap_control_policy.yaml"
        self.policy = load_yaml_file(self.policy_path, critical=True, root=PATHS.project_root)
        self.registry = registry or ServiceRegistryService()
        self.health = health or ServiceHealthChecker()
        self.audit = audit or SupervisorAuditService()
        self.traces = traces or SupervisorTraceService()
        self.events = events or MonitorEventService(audit=self.audit)
        self.runner = runner
        self.state_path = PATHS.project_root / "data" / "runtime" / "supervisor" / "bootstrap_control_state.json"

    def status(self) -> BootstrapControlStatus:
        service_id = str(self._config("controlled_service_id", "monitor_supervisor"))
        service = self.registry.get(service_id)
        bootstrap_port = int(self._config("bootstrap_port", 9080))
        controlled_port = int(self._config("controlled_port", 9099))
        state = self._read_state()
        health = self.health.check(service) if service is not None else ServiceHealth(service_id=service_id, status="unknown", human_message="Servico monitor_supervisor nao encontrado no manifest.")
        if state.get("status") == "restarting" and (time.time() - float(state.get("started_at_epoch", 0) or 0)) < int(self._config("restart_timeout_seconds", 60)):
            status = "restarting"
            human = "Monitor 9099 esta reiniciando pelo bootstrap 9080."
        elif health.status == "healthy":
            status = "online"
            human = "Monitor supervisor 9099 esta online."
        elif health.status == "degraded":
            status = "degraded"
            human = "Monitor supervisor 9099 respondeu, mas esta degradado."
        elif health.status == "down":
            status = "offline"
            human = "Monitor supervisor 9099 esta offline."
        else:
            status = "unknown"
            human = health.human_message or "Estado do monitor 9099 nao confirmado."
        return BootstrapControlStatus(
            status=status,
            service_id=service_id,
            bootstrap_port=bootstrap_port,
            controlled_port=controlled_port,
            health=health,
            last_restart_id=state.get("restart_id"),
            human_message=human,
        )

    def restart_monitor(self, *, requested_by: str = "local_operator", device_id: str | None = None, reason: str | None = None) -> BootstrapControlRestartResult:
        service_id = str(self._config("controlled_service_id", "monitor_supervisor"))
        bootstrap_port = int(self._config("bootstrap_port", 9080))
        controlled_port = int(self._config("controlled_port", 9099))
        if not bool(self._config("enabled", False)):
            return self._blocked("bootstrap_control_disabled", service_id=service_id, bootstrap_port=bootstrap_port, controlled_port=controlled_port, requested_by=requested_by, device_id=device_id)
        if not bool(self._config("no_custom_command_from_request", True)):
            return self._blocked("bootstrap_policy_requires_no_custom_command", service_id=service_id, bootstrap_port=bootstrap_port, controlled_port=controlled_port, requested_by=requested_by, device_id=device_id)
        service = self.registry.get(service_id)
        if service is None:
            return self._blocked("controlled_service_not_found", service_id=service_id, bootstrap_port=bootstrap_port, controlled_port=controlled_port, requested_by=requested_by, device_id=device_id)
        if int(service.port) != controlled_port:
            return self._blocked("controlled_service_port_mismatch", service_id=service_id, bootstrap_port=bootstrap_port, controlled_port=controlled_port, requested_by=requested_by, device_id=device_id)

        pre = self.health.check(service)
        restart_id = f"monitor_restart_{int(time.time() * 1000)}"
        self._write_state({"status": "restarting", "restart_id": restart_id, "started_at_epoch": time.time()})
        self.events.record(MonitorEvent(event_type="monitor_restart_started_by_bootstrap", service_id=service_id, port=controlled_port, status="restarting", message="Restart governado do monitor 9099 iniciado pelo bootstrap 9080."))
        trace_events: list[dict[str, Any]] = [{"event": "pre_health", "status": pre.status}]
        stop_result = self._run_script("stop", controlled_port=controlled_port)
        trace_events.append({"event": "stop_script", **stop_result})
        start_result = self._run_script("start", controlled_port=controlled_port)
        trace_events.append({"event": "start_script", **start_result})
        post = self.health.check(service, timeout_seconds=float(self._config("status_timeout_seconds", 1.0)))
        trace_events.append({"event": "post_health", "status": post.status})
        command_ok = stop_result.get("returncode") == 0 and start_result.get("returncode") == 0
        status = "accepted" if command_ok and post.status == "healthy" else ("degraded" if command_ok else "failed")
        self._write_state({"status": "online" if post.status == "healthy" else post.status, "restart_id": restart_id, "finished_at_epoch": time.time()})
        trace = self.traces.record(SupervisorTrace(action="bootstrap_restart_monitor", service_id=service_id, port=controlled_port, status=status, events=trace_events))
        audit = self.audit.record(SupervisorAudit(action="bootstrap_restart_monitor", service_id=service_id, port=controlled_port, requested_by=requested_by, device_id=device_id, status=status, data={"reason": reason, "bootstrap_port": bootstrap_port, "canonical_scripts": True}))
        self.events.record(MonitorEvent(event_type="monitor_restart_finished_by_bootstrap", service_id=service_id, port=controlled_port, status=status, message="Restart governado do monitor 9099 finalizado.", data={"post_health": post.status}))
        return BootstrapControlRestartResult(
            restart_id=restart_id,
            status=status,
            allowed=True,
            service_id=service_id,
            bootstrap_port=bootstrap_port,
            controlled_port=controlled_port,
            pre_health=pre,
            post_health=post,
            audit_id=audit.audit_id,
            trace_id=trace.trace_id,
            warnings=[] if status == "accepted" else [f"post_health:{post.status}", f"stop:{stop_result.get('returncode')}", f"start:{start_result.get('returncode')}"],
            human_message="Monitor supervisor 9099 reiniciado pelo bootstrap 9080." if status == "accepted" else "Restart do monitor solicitado, mas o estado saudavel nao foi confirmado.",
        )

    def _run_script(self, key: str, *, controlled_port: int) -> dict[str, Any]:
        scripts = self._config("canonical_scripts", {})
        rel = scripts.get(key) if isinstance(scripts, dict) else None
        script = self._script_path(str(rel or ""))
        if script is None:
            return {"returncode": 127, "error": "canonical_script_missing"}
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Port",
            str(controlled_port),
        ]
        timeout = int(self._config("restart_timeout_seconds", 60))
        try:
            result = self.runner(command, cwd=str(PATHS.project_root), timeout=timeout, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
            return {"returncode": result.returncode, "stdout_tail": (result.stdout or "")[-500:], "stderr_tail": (result.stderr or "")[-500:]}
        except subprocess.TimeoutExpired:
            return {"returncode": 124, "error": "canonical_script_timeout"}
        except Exception as exc:
            return {"returncode": 1, "error": exc.__class__.__name__}

    def _script_path(self, relative_path: str) -> Path | None:
        if not relative_path:
            return None
        candidate = (PATHS.project_root / relative_path).resolve(strict=False)
        root = PATHS.project_root.resolve(strict=False)
        if not (candidate == root or root in candidate.parents):
            return None
        if not candidate.exists() or candidate.suffix.lower() != ".ps1":
            return None
        return candidate

    def _blocked(self, reason: str, *, service_id: str, bootstrap_port: int, controlled_port: int, requested_by: str, device_id: str | None) -> BootstrapControlRestartResult:
        trace = self.traces.record(SupervisorTrace(action="bootstrap_restart_monitor", service_id=service_id, port=controlled_port, status="blocked", events=[{"event": "blocked", "reason": reason}]))
        audit = self.audit.record(SupervisorAudit(action="bootstrap_restart_monitor", service_id=service_id, port=controlled_port, requested_by=requested_by, device_id=device_id, status="blocked", data={"reason": reason, "bootstrap_port": bootstrap_port}))
        self.events.record(MonitorEvent(event_type="monitor_restart_blocked_by_bootstrap", service_id=service_id, port=controlled_port, status="blocked", message=reason))
        return BootstrapControlRestartResult(status="blocked", allowed=False, service_id=service_id, bootstrap_port=bootstrap_port, controlled_port=controlled_port, audit_id=audit.audit_id, trace_id=trace.trace_id, blocked_reasons=[reason], human_message="Restart do monitor bloqueado pela policy do bootstrap control.")

    def _config(self, key: str, default: Any) -> Any:
        section = self.policy.get("bootstrap_control", {}) if isinstance(self.policy, dict) else {}
        return section.get(key, default) if isinstance(section, dict) else default

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_state(self, payload: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        temp.replace(self.state_path)
