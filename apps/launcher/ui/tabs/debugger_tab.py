from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from apps.launcher.ui.components.component_base import COLORS, EventCard, NeonButton, ScrollableFrame, TextCard


class DebuggerTab(ttk.Frame):
    def __init__(self, parent, debugger_client, event_client, event_contract_client) -> None:
        super().__init__(parent)
        self.debugger_client = debugger_client
        self.event_client = event_client
        self.event_contract_client = event_contract_client
        bar = tk.Frame(self, background=COLORS["background"]); bar.pack(fill="x", padx=8, pady=8)
        self.severity = tk.Entry(bar, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 12))
        self.severity.insert(0, "")
        self.severity.pack(side="left", padx=(0, 8), ipady=8)
        NeonButton(bar, "Filtrar/Atualizar", command=self.refresh).pack(side="left", padx=4)
        self.scroll = ScrollableFrame(self); self.scroll.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self) -> None:
        for child in self.scroll.body.winfo_children(): child.destroy()
        TextCard(self.scroll.body, "Debugger status", str(self.debugger_client.status().data)).pack(fill="x", padx=8, pady=4)
        requested = self.severity.get().strip()
        query = f"severity={requested}" if requested else ""
        multi_agent = self.debugger_client.events(query)
        if multi_agent.ok:
            events = multi_agent.data.get("events", [])
            TextCard(
                self.scroll.body,
                "Multi-Agent Debugger",
                f"{len(events)} eventos sanitizados. Raw oculto por padrao.",
                "Fonte: /api/v1/debugger/events",
                height=3,
            ).pack(fill="x", padx=8, pady=4)
            for event in events[:100]:
                title = str(event.get("event_type", "evento"))
                body = str(event.get("human_message", ""))
                meta = f"agent={event.get('agent_id') or 'n/a'} run={event.get('run_id') or 'n/a'} status={event.get('status', 'unknown')} severity={event.get('severity', 'info')}"
                TextCard(self.scroll.body, title, body, meta, height=4).pack(fill="x", padx=8, pady=4)
            return
        contracts = self.event_contract_client.contracts(); known = set((contracts.data.get("contracts") or {}).keys()) if contracts.ok else set()
        events = self.event_client.list_events(limit=100)
        if events.ok:
            for event in events.data.get("events", []):
                if requested and event.get("severity") != requested: continue
                if self.event_client.displayable(event, known):
                    EventCard.from_event(self.scroll.body, event).pack(fill="x", padx=8, pady=4)
        else:
            TextCard(self.scroll.body, "Eventos", str(events.error)).pack(fill="x", padx=8, pady=4)
