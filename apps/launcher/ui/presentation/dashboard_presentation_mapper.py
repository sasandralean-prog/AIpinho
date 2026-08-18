from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ServicePresentation:
    title: str
    status: str
    summary: str
    port: int | None = None
    service_id: str | None = None
    restart_allowed: bool = False


class DashboardPresentationMapper:
    def services(self, status_payload: dict[str, Any], ports_payload: dict[str, Any]) -> list[ServicePresentation]:
        services = self._service_items(status_payload) or self._service_items(ports_payload)
        if services:
            return [self._service(item) for item in services if isinstance(item, dict)]
        return [self._summary(status_payload, ports_payload)]

    def _service_items(self, payload: dict[str, Any]) -> list[Any]:
        for key in ("services", "items", "ports"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return []

    def _service(self, item: dict[str, Any]) -> ServicePresentation:
        port = self._int(item.get("port"))
        status = str(item.get("status") or item.get("state") or "unknown")
        title = str(item.get("display_name") or item.get("service_id") or item.get("name") or f"Porta {port or '?'}")
        summary = str(item.get("human_message") or item.get("summary") or self._status_summary(status, port))
        return ServicePresentation(
            title=title,
            status=status,
            summary=summary,
            port=port,
            service_id=str(item.get("service_id") or "") or None,
            restart_allowed=bool(item.get("restartable") or item.get("monitor_can_restart")),
        )

    def _summary(self, status_payload: dict[str, Any], ports_payload: dict[str, Any]) -> ServicePresentation:
        status = str(status_payload.get("status") or ports_payload.get("status") or "unknown")
        summary = str(status_payload.get("human_summary") or status_payload.get("message") or "Status recebido do backend.")
        return ServicePresentation(title="AIpinho", status=status, summary=summary)

    def _status_summary(self, status: str, port: int | None) -> str:
        if status.lower() in {"ok", "online", "running"}:
            return f"Servico online{f' na porta {port}' if port else ''}."
        if status.lower() in {"down", "offline", "failed"}:
            return f"Servico indisponivel{f' na porta {port}' if port else ''}."
        return f"Estado atual: {status}."

    def _int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
