from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.supervisor.contracts import (
    BackendControlRestartResult,
    BackendControlStatus,
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


class BackendControlService:
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
        self.policy_path = policy_path or PATHS.config_root / "supervisor" / "backend_control_policy.yaml"
        self.policy = load_yaml_file(self.policy_path, critical=True, root=PATHS.project_root)
        self.registry = registry or ServiceRegistryService()
        self.health = health or ServiceHealthChecker()
        self.audit = audit or SupervisorAuditService()
        self.traces = traces or SupervisorTraceService()
        self.events = events or MonitorEventService(audit=self.audit)
        self.runner = runner
        self.state_path = PATHS.project_root / "data" / "runtime" / "supervisor" / "backend_control_state.json"

    def status(self) -> BackendControlStatus:
        service = self.registry.get(self._config("controlled_service_id", "core_backend"))
        backend_port = int(self._config("controlled_port", 9088))
        control_port = int(self._config("control_port", 9099))
        state = self._read_state()
        health = self.health.check(service) if service is not None else ServiceHealth(service_id="core_backend", status="unknown", human_message="Servico core_backend nao encontrado no manifest.")
        if state.get("status") == "restarting" and (time.time() - float(state.get("started_at_epoch", 0) or 0)) < int(self._config("restart_timeout_seconds", 90)):
            status = "restarting"
            human = "Backend esta reiniciando pelo supervisor na porta 9099."
        elif health.status == "healthy":
            status = "online"
            human = "Backend principal esta online."
        elif health.status == "degraded":
            status = "degraded"
            human = "Backend respondeu, mas esta degradado."
        elif health.status == "down":
            status = "offline"
            human = "Backend principal esta offline."
        else:
            status = "unknown"
            human = health.human_message or "Estado do backend nao confirmado."
        return BackendControlStatus(
            status=status,
            service_id=self._config("controlled_service_id", "core_backend"),
            backend_port=backend_port,
            control_port=control_port,
            exclusive_control_port=bool(self._config("exclusive_control_port", True)),
            health=health,
            last_restart_id=state.get("restart_id"),
            human_message=human,
        )

    def restart(self, *, served_port: int | None, requested_by: str = "mobile_operator", device_id: str | None = None, reason: str | None = None) -> BackendControlRestartResult:
        control_port = int(self._config("control_port", 9099))
        backend_port = int(self._config("controlled_port", 9088))
        service_id = str(self._config("controlled_service_id", "core_backend"))
        if not bool(self._config("enabled", False)):
            return self._blocked("backend_control_disabled", service_id=service_id, backend_port=backend_port, control_port=control_port, requested_by=requested_by, device_id=device_id)
        if bool(self._config("exclusive_control_port", True)) and served_port not in {control_port, None}:
            return self._blocked("backend_control_port_required", service_id=service_id, backend_port=backend_port, control_port=control_port, requested_by=requested_by, device_id=device_id)
        service = self.registry.get(service_id)
        if service is None:
            return self._blocked("controlled_service_not_found", service_id=service_id, backend_port=backend_port, control_port=control_port, requested_by=requested_by, device_id=device_id)
        pre = self.health.check(service)
        restart_id = f"backend_restart_{int(time.time() * 1000)}"
        self._write_state({"status": "restarting", "restart_id": restart_id, "started_at_epoch": time.time()})
        trace_events: list[dict[str, Any]] = [{"event": "pre_health", "status": pre.status}]
        self.events.record(MonitorEvent(event_type="backend_restart_started", service_id=service_id, port=backend_port, status="restarting", message="Restart governado iniciado pelo backend control."))
        stop_result = self._run_script("stop", backend_port=backend_port)
        trace_events.append({"event": "stop_script", **stop_result})
        start_result = self._run_script("start", backend_port=backend_port)
        trace_events.append({"event": "start_script", **start_result})
        post = self.health.check(service, timeout_seconds=float(self._config("status_timeout_seconds", 1.0)))
        trace_events.append({"event": "post_health", "status": post.status})
        command_ok = stop_result.get("returncode") == 0 and start_result.get("returncode") == 0
        status = "accepted" if command_ok and post.status == "healthy" else ("degraded" if command_ok else "failed")
        self._write_state({"status": "online" if post.status == "healthy" else post.status, "restart_id": restart_id, "finished_at_epoch": time.time()})
        trace = self.traces.record(SupervisorTrace(action="backend_control_restart", service_id=service_id, port=backend_port, status=status, events=trace_events))
        audit = self.audit.record(SupervisorAudit(action="backend_control_restart", service_id=service_id, port=backend_port, requested_by=requested_by, device_id=device_id, status=status, data={"reason": reason, "control_port": control_port, "canonical_scripts": True}))
        self.events.record(MonitorEvent(event_type="backend_restart_finished", service_id=service_id, port=backend_port, status=status, message="Restart governado finalizado.", data={"post_health": post.status}))
        return BackendControlRestartResult(
            restart_id=restart_id,
            status=status,
            allowed=True,
            service_id=service_id,
            backend_port=backend_port,
            control_port=control_port,
            pre_health=pre,
            post_health=post,
            audit_id=audit.audit_id,
            trace_id=trace.trace_id,
            warnings=[] if status == "accepted" else [f"post_health:{post.status}", f"stop:{stop_result.get('returncode')}", f"start:{start_result.get('returncode')}"],
            human_message="Backend reiniciado pelos scripts canonicos." if status == "accepted" else "Restart solicitado, mas o backend nao confirmou estado saudavel.",
        )

    def _run_script(self, key: str, *, backend_port: int) -> dict[str, Any]:
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
            str(backend_port),
        ]
        timeout = int(self._config("restart_timeout_seconds", 90))
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

    def _blocked(self, reason: str, *, service_id: str, backend_port: int, control_port: int, requested_by: str, device_id: str | None) -> BackendControlRestartResult:
        trace = self.traces.record(SupervisorTrace(action="backend_control_restart", service_id=service_id, port=backend_port, status="blocked", events=[{"event": "blocked", "reason": reason}]))
        audit = self.audit.record(SupervisorAudit(action="backend_control_restart", service_id=service_id, port=backend_port, requested_by=requested_by, device_id=device_id, status="blocked", data={"reason": reason, "control_port": control_port}))
        self.events.record(MonitorEvent(event_type="backend_restart_blocked", service_id=service_id, port=backend_port, status="blocked", message=reason))
        return BackendControlRestartResult(status="blocked", allowed=False, service_id=service_id, backend_port=backend_port, control_port=control_port, audit_id=audit.audit_id, trace_id=trace.trace_id, blocked_reasons=[reason], human_message="Restart bloqueado pela policy do backend control.")

    def _config(self, key: str, default: Any) -> Any:
        section = self.policy.get("backend_control", {}) if isinstance(self.policy, dict) else {}
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

    def status_payload(self) -> dict[str, object]:
        return {"status": "ok", "service": "backend_control", "backend": self.status().model_dump()}
