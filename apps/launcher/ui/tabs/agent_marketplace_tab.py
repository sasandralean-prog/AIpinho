from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any

from apps.launcher.ui.components.component_base import (
    ActionCard,
    COLORS,
    NeonButton,
    PlaceholderEntry,
    RawCollapsible,
    ScrollableFrame,
    TextCard,
)


class AgentMarketplaceTab(ttk.Frame):
    def __init__(self, parent, marketplace_client) -> None:
        super().__init__(parent)
        self.marketplace_client = marketplace_client
        self._last_payload: dict[str, Any] = {}
        self._build_toolbar()
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.refresh()

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, background=COLORS["background"])
        bar.pack(fill="x", padx=8, pady=8)
        NeonButton(bar, "Atualizar", command=self.refresh).pack(side="left", padx=(0, 8))
        self.capability_entry = PlaceholderEntry(bar, "capability: ocr, coding, review...", background=COLORS["card"])
        self.capability_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        NeonButton(bar, "Buscar capability", command=self._query_capability, accent=COLORS["green"]).pack(side="left")

    def refresh(self) -> None:
        self._clear()
        snapshot = self.marketplace_client.snapshot()
        payload = snapshot.data if snapshot.ok and isinstance(snapshot.data, dict) else {"error": snapshot.error}
        self._last_payload = payload
        TextCard(
            self.scroll.body,
            "Agent Marketplace",
            self._summary(payload),
            "Fonte canonica: /api/v1/agent-marketplace",
            height=5,
        ).pack(fill="x", padx=8, pady=6)
        for agent in payload.get("agents", []) if isinstance(payload, dict) else []:
            self._render_agent(agent, payload)
        capabilities = payload.get("capabilities", {}) if isinstance(payload, dict) else {}
        TextCard(
            self.scroll.body,
            "Capability Marketplace",
            json.dumps(capabilities, ensure_ascii=False, indent=2),
            "Planner consulta capabilities; nao providers.",
            height=10,
        ).pack(fill="x", padx=8, pady=6)
        RawCollapsible(self.scroll.body, lambda: self._last_payload).pack(fill="x", padx=8, pady=6)

    def _clear(self) -> None:
        if not hasattr(self, "scroll"):
            return
        for child in self.scroll.body.winfo_children():
            child.destroy()

    def _summary(self, payload: dict[str, Any]) -> str:
        agents = payload.get("agents", []) if isinstance(payload.get("agents"), list) else []
        capabilities = payload.get("capabilities", {}) if isinstance(payload.get("capabilities"), dict) else {}
        warnings = payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []
        return (
            f"Status: {payload.get('status', '-')}\n"
            f"Agentes registrados: {len(agents)}\n"
            f"Capabilities descobertas: {len(capabilities)}\n"
            f"Warnings: {', '.join(warnings) if warnings else 'nenhum'}\n"
            "Selecao e failover sao feitos por manifest, health, trust, custo, latencia e prioridade."
        )

    def _render_agent(self, agent: dict[str, Any], payload: dict[str, Any]) -> None:
        health_map = {
            item.get("agent_id"): item
            for item in payload.get("health", [])
            if isinstance(item, dict)
        }
        health = health_map.get(agent.get("agent_id"), {})
        capabilities = [item.get("capability_id") for item in agent.get("capabilities", []) if isinstance(item, dict)]
        summary = (
            f"agent_id={agent.get('agent_id', '-')}\n"
            f"Trust: {agent.get('trust_level', '-')} | Runtime: {agent.get('runtime_profile', '-')}\n"
            f"Health: {health.get('health_status', agent.get('health_status', '-'))} | Auto disabled: {health.get('auto_disabled', False)}\n"
            f"Latency: {agent.get('latency_ms', '-')}ms | Cost: {agent.get('cost', '-')} | Priority: {agent.get('priority', '-')}\n"
            f"Capabilities: {', '.join(capabilities) if capabilities else '-'}"
        )
        card = ActionCard(
            self.scroll.body,
            str(agent.get("name") or agent.get("agent_id") or "Agent"),
            summary,
            f"version={agent.get('version', '-')}",
        )
        NeonButton(card.actions, "Heartbeat", command=lambda value=str(agent.get("agent_id") or ""): self._heartbeat(value)).pack(side="left")
        card.pack(fill="x", padx=8, pady=4)

    def _query_capability(self) -> None:
        capability = self.capability_entry.get_value()
        if not capability:
            return
        result = self.marketplace_client.query_capability(capability)
        TextCard(
            self.scroll.body,
            f"Capability: {capability}",
            json.dumps(result.data if result.ok else {"error": result.error, "data": result.data}, ensure_ascii=False, indent=2),
            "Negotiation result",
            height=10,
        ).pack(fill="x", padx=8, pady=6)

    def _heartbeat(self, agent_id: str) -> None:
        if not agent_id:
            return
        self.marketplace_client.heartbeat(agent_id)
        self.refresh()
