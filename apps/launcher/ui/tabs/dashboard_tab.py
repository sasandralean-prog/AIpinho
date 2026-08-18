from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from apps.launcher.ui.components.component_base import ActionCard, COLORS, EventCard, NeonButton, ScrollableFrame, TextCard
from apps.launcher.ui.presentation import DashboardPresentationMapper


class DashboardTab(ttk.Frame):
    def __init__(self, parent, dashboard_client, monitor_client, event_client, event_contract_client) -> None:
        super().__init__(parent)
        self.dashboard_client = dashboard_client
        self.monitor_client = monitor_client
        self.event_client = event_client
        self.event_contract_client = event_contract_client
        self.mapper = DashboardPresentationMapper()
        bar = tk.Frame(self, background=COLORS["background"])
        bar.pack(fill="x", padx=8, pady=8)
        NeonButton(bar, "Atualizar", command=self.refresh).pack(side="left")
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.refresh()

    def _clear(self) -> None:
        for child in self.scroll.body.winfo_children():
            child.destroy()

    def refresh(self) -> None:
        self._clear()
        multi_agent = self.dashboard_client.multi_agent()
        if multi_agent.ok:
            data = multi_agent.data
            TextCard(
                self.scroll.body,
                "Multi-Agent Dashboard",
                f"backend={data.get('backend_status', 'unknown')} agents={len(data.get('agents', []))} active_runs={len(data.get('active_runs', []))} pending_approvals={len(data.get('pending_approvals', []))}",
                "Fonte: /api/v1/dashboard/multi-agent",
                height=3,
            ).pack(fill="x", padx=8, pady=6)
            for card_data in data.get("cards", [])[:12]:
                ActionCard(
                    self.scroll.body,
                    str(card_data.get("title", "Card")),
                    str(card_data.get("summary", "")),
                    f"status={card_data.get('status', 'unknown')} severity={card_data.get('severity', 'info')} count={card_data.get('count', '')}",
                ).pack(fill="x", padx=8, pady=4)
        else:
            TextCard(self.scroll.body, "Multi-Agent Dashboard", str(multi_agent.error), "Endpoint novo indisponivel ou degradado.", height=4).pack(fill="x", padx=8, pady=6)
        status = self.monitor_client.status()
        ports = self.monitor_client.ports()
        services = self.monitor_client.services()
        service_payload = services.data if services.ok else status.data if status.ok else {}
        ports_payload = ports.data if ports.ok else {}
        for service in self.mapper.services(service_payload, ports_payload):
            card = ActionCard(
                self.scroll.body,
                service.title,
                service.summary,
                f"status={service.status} porta={service.port or 'n/a'}",
            )
            if service.service_id and service.port and self.monitor_client.can_restart_port(service.port):
                NeonButton(
                    card.actions,
                    "Reiniciar",
                    command=lambda svc=service.service_id, port=service.port: self._restart(svc, port),
                ).pack(side="left")
            elif service.port == 9099:
                tk.Label(card.actions, text="9099: monitor", background=COLORS["card"], foreground=COLORS["pink"]).pack(side="left", padx=(0, 8))
                NeonButton(
                    card.actions,
                    "Reiniciar via 9080",
                    command=self._restart_monitor,
                ).pack(side="left")
            card.pack(fill="x", padx=8, pady=6)
        for title, result in [("Recursos", self.monitor_client.resources()), ("Event Registry", self.event_contract_client.status())]:
            TextCard(self.scroll.body, title, str(result.data if result.ok else result.error)).pack(fill="x", padx=8, pady=6)
        events = self.event_client.list_events(limit=25)
        contracts = self.event_contract_client.contracts()
        known = set((contracts.data.get("contracts") or {}).keys()) if contracts.ok else set()
        if events.ok:
            for event in events.data.get("events", []):
                if self.event_client.displayable(event, known):
                    EventCard.from_event(self.scroll.body, event).pack(fill="x", padx=8, pady=4)
        else:
            TextCard(self.scroll.body, "Eventos", str(events.error)).pack(fill="x", padx=8, pady=6)

    def _restart(self, service_id: str, port: int) -> None:
        result = self.monitor_client.restart_service(service_id, port)
        TextCard(
            self.scroll.body,
            "Restart",
            str(result.data if result.ok else result.error),
            f"service_id={service_id} port={port}",
            height=3,
        ).pack(fill="x", padx=8, pady=4)

    def _restart_monitor(self) -> None:
        result = self.monitor_client.restart_monitor_via_bootstrap()
        TextCard(
            self.scroll.body,
            "Restart monitor 9099",
            str(result.data if result.ok else result.error),
            "Canal bootstrap: 9080",
            height=3,
        ).pack(fill="x", padx=8, pady=4)
