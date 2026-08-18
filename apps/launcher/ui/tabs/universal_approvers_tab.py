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


class UniversalApproversTab(ttk.Frame):
    def __init__(self, parent, approver_client) -> None:
        super().__init__(parent)
        self.approver_client = approver_client
        self._last_payload: dict[str, Any] = {}
        self._build_toolbar()
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.refresh()

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, background=COLORS["background"])
        bar.pack(fill="x", padx=8, pady=8)
        NeonButton(bar, "Atualizar", command=self.refresh).pack(side="left", padx=(0, 8))

        self.approval_entry = PlaceholderEntry(bar, "approval_id", background=COLORS["card"])
        self.approval_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.approver_entry = PlaceholderEntry(bar, "approver_id", background=COLORS["card"])
        self.approver_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.decision_entry = PlaceholderEntry(bar, "texto da decisao", background=COLORS["card"])
        self.decision_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        NeonButton(bar, "Registrar decisao", command=self._send_text_decision, accent=COLORS["green"]).pack(side="left")

    def refresh(self) -> None:
        self._clear()
        approvers = self.approver_client.list_approvers()
        timeline = self.approver_client.timeline(limit=100)
        mobile_view = self.approver_client.mobile_view()
        payload = {
            "approvers": approvers.data if approvers.ok else {"error": approvers.error},
            "timeline": timeline.data if timeline.ok else {"error": timeline.error},
            "mobile_view": mobile_view.data if mobile_view.ok else {"error": mobile_view.error},
        }
        self._last_payload = payload

        TextCard(
            self.scroll.body,
            "Universal Approvers",
            self._summary(approvers, timeline),
            "Fonte canonica: /api/v1/universal-approvers",
            height=4,
        ).pack(fill="x", padx=8, pady=6)

        if approvers.ok and isinstance(approvers.data, dict):
            for approver in approvers.data.get("approvers", []):
                self._render_approver(approver)
        else:
            TextCard(self.scroll.body, "Approvers indisponiveis", str(approvers.error), height=4).pack(fill="x", padx=8, pady=6)

        if timeline.ok and isinstance(timeline.data, dict):
            self._render_timeline(timeline.data.get("items", []))
        else:
            TextCard(self.scroll.body, "Approval Timeline indisponivel", str(timeline.error), height=4).pack(fill="x", padx=8, pady=6)

        RawCollapsible(self.scroll.body, lambda: self._last_payload).pack(fill="x", padx=8, pady=6)

    def _clear(self) -> None:
        if not hasattr(self, "scroll"):
            return
        for child in self.scroll.body.winfo_children():
            child.destroy()

    def _summary(self, approvers: Any, timeline: Any) -> str:
        approver_count = len(approvers.data.get("approvers", [])) if approvers.ok and isinstance(approvers.data, dict) else 0
        event_count = len(timeline.data.get("items", [])) if timeline.ok and isinstance(timeline.data, dict) else 0
        return (
            "Authority: AIpinho\n"
            f"Approvers registrados: {approver_count}\n"
            f"Eventos/approvals na timeline: {event_count}\n"
            "Decisoes externas continuam sem permissao de executar diretamente; o runtime governado retoma a task."
        )

    def _render_approver(self, approver: dict[str, Any]) -> None:
        capabilities = approver.get("capabilities") if isinstance(approver.get("capabilities"), dict) else {}
        capability_lines = [
            f"{category}: {', '.join(values)}"
            for category, values in sorted(capabilities.items())
            if values
        ]
        summary = (
            f"Tipo: {approver.get('approver_type', '-')}\n"
            f"Trust: {approver.get('trust_level', '-')}\n"
            f"Status: {approver.get('status', '-')}\n"
            + ("\n".join(capability_lines[:8]) if capability_lines else "Sem capabilities declaradas.")
        )
        card = ActionCard(
            self.scroll.body,
            str(approver.get("display_name") or approver.get("approver_id") or "Approver"),
            summary,
            f"approver_id={approver.get('approver_id', '-')}",
        )
        NeonButton(card.actions, "Usar approver", command=lambda item=approver: self._fill_approver(item)).pack(side="left")
        card.pack(fill="x", padx=8, pady=4)

    def _render_timeline(self, items: list[dict[str, Any]]) -> None:
        TextCard(
            self.scroll.body,
            "Approval Timeline",
            f"{len(items)} approvals recentes com origem, assinatura e authority.",
            "Fonte: /api/v1/universal-approvers/approval-timeline",
            height=2,
        ).pack(fill="x", padx=8, pady=6)
        for item in items[:40]:
            signature = item.get("signature") or {}
            origin = item.get("origin") or {}
            summary = (
                f"status={item.get('status', '-')}\n"
                f"operation_type={item.get('operation_type', '-')}\n"
                f"actions={', '.join(item.get('actions_requested') or [])}\n"
                f"approved_by={origin.get('approved_by') or item.get('approver_id') or '-'}\n"
                f"authority={item.get('authority', 'AIpinho')}\n"
                f"signature={signature.get('signature_id', '-')}"
            )
            card = ActionCard(
                self.scroll.body,
                str(item.get("approval_id") or "approval"),
                summary,
                f"updated_at={item.get('updated_at', '-')}",
            )
            NeonButton(card.actions, "Copiar approval_id", command=lambda value=str(item.get("approval_id") or ""): self._copy(value)).pack(side="left")
            card.pack(fill="x", padx=8, pady=4)
            RawCollapsible(self.scroll.body, lambda item=item: item).pack(fill="x", padx=8, pady=2)

    def _fill_approver(self, approver: dict[str, Any]) -> None:
        self.approver_entry.delete(0, "end")
        self.approver_entry.insert(0, str(approver.get("approver_id") or ""))
        self.approver_entry.configure(foreground=COLORS["green"])
        self.approver_entry._showing_placeholder = False

    def _send_text_decision(self) -> None:
        approval_id = self.approval_entry.get_value()
        approver_id = self.approver_entry.get_value()
        decision_text = self.decision_entry.get_value()
        if not approval_id or not approver_id or not decision_text:
            TextCard(
                self.scroll.body,
                "Decisao universal",
                "Preencha approval_id, approver_id e texto da decisao.",
                "Nenhuma chamada foi enviada.",
                height=3,
            ).pack(fill="x", padx=8, pady=4)
            return
        result = self.approver_client.text_decision(
            approval_id,
            approver_id=approver_id,
            text=decision_text,
            reason="launcher_universal_approver_decision",
        )
        TextCard(
            self.scroll.body,
            "Decisao universal",
            json.dumps(result.data if result.ok else {"error": result.error, "data": result.data}, ensure_ascii=False, indent=2),
            f"approval_id={approval_id} approver_id={approver_id}",
            height=8,
        ).pack(fill="x", padx=8, pady=4)
        self.refresh()

    def _copy(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
