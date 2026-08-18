from __future__ import annotations

from typing import Any

from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService
from aipinho.services.supervisor.backend_control_service import BackendControlService


class HealthSemanticsService:
    """Separates backend liveness from operational and observability state."""

    def status(self) -> dict[str, Any]:
        control_plane = self._safe(lambda: BackendControlService().status().model_dump())
        observability = self._safe(lambda: MultiAgentObservabilityService().health())
        control_plane_state = str(control_plane.get("status") or "unknown")
        backend_state = "online"
        observability_state = str(observability.get("status") or "unknown")
        operational_state = self._operational_state(backend_state, observability_state)
        top_level_status = "degraded" if observability_state in {"degraded", "partial", "blocked"} else "ok"
        return {
            "status": top_level_status,
            "backend_health": {
                "status": backend_state,
                "meaning": "Processo HTTP principal respondeu ou esta em transicao conhecida.",
                "source": "api_liveness",
                "control_plane_status": control_plane_state,
                "control_plane_source": "backend_control",
            },
            "operational_health": {
                "status": operational_state,
                "meaning": "Capacidade de executar fluxo comum com policy, tool gateway e estado coerente.",
                "source": "health_semantics",
            },
            "observability_health": {
                "status": observability_state,
                "meaning": "Qualidade dos traces, runs, eventos, approvals e dashboard; pode degradar sem derrubar o backend.",
                "source": "multi_agent_observability",
                "warnings": observability.get("warnings", []),
            },
            "port_9099": {
                "role": "monitor_supervisor_control_plane",
                "exclusive": True,
                "self_restart_allowed": False,
                "meaning": "Porta de controle/supervisao; nao deve ser tratada como backend principal offline.",
            },
        }

    def _operational_state(self, backend_state: str, observability_state: str) -> str:
        if backend_state in {"down", "offline", "failed"}:
            return "offline"
        return "ok"

    def _safe(self, factory) -> dict[str, Any]:
        try:
            value = factory()
            return value if isinstance(value, dict) else {"status": "ok", "value": value}
        except Exception as exc:
            return {"status": "degraded", "error": type(exc).__name__}
