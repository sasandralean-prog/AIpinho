from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from apps.launcher.ui.components.component_base import ActionCard, COLORS, NeonButton, RawCollapsible, ScrollableFrame, TextCard
from apps.launcher.ui.presentation import PipelinePresentationMapper


class PlanningTab(ttk.Frame):
    def __init__(self, parent, pipeline_client) -> None:
        super().__init__(parent)
        self.pipeline_client = pipeline_client
        self.mapper = PipelinePresentationMapper()
        bar = tk.Frame(self, background=COLORS["background"])
        bar.pack(fill="x", padx=8, pady=8)
        NeonButton(bar, "Atualizar", command=self.refresh).pack(side="left")
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self) -> None:
        for child in self.scroll.body.winfo_children():
            child.destroy()
        result = self.pipeline_client.mobile_pipeline()
        if not result.ok or not isinstance(result.data, dict):
            TextCard(
                self.scroll.body,
                "Planning",
                str(result.error or result.data),
                "Fonte: /api/v1/mobile/view-model/pipeline",
                height=4,
            ).pack(fill="x", padx=8, pady=4)
            return
        report = self._planning_report_from_payload(result.data)
        if not report or report.get("status") == "none":
            TextCard(
                self.scroll.body,
                "Planning",
                "Nenhum Planning Report selecionado pelo view-model mobile.",
                "Fonte: task_run.intent_map.planning_report",
                height=3,
            ).pack(fill="x", padx=8, pady=4)
            self._render_mobile_cards(result.data)
            return
        nodes = report.get("nodes") if isinstance(report.get("nodes"), list) else []
        groups = report.get("parallel_groups") if isinstance(report.get("parallel_groups"), list) else []
        lines = [
            f"Planning Report: {report.get('report_id')}",
            f"Status: {report.get('status')} | Tipo: {report.get('task_type')} | Complexidade: {report.get('complexity')}",
            f"Estrategia: {report.get('strategy')}",
            f"Risco: {report.get('risk_level')} | Steps estimados: {report.get('estimated_steps')}",
            f"Approval: {report.get('approval_required')} | Review: {report.get('review_required')}",
            "",
            "Parallel groups:",
        ]
        for group in groups:
            if isinstance(group, list):
                lines.append("- " + ", ".join(str(item) for item in group))
        lines.append("")
        lines.append("Nodes:")
        for node in nodes:
            if not isinstance(node, dict):
                continue
            deps = node.get("dependencies") if isinstance(node.get("dependencies"), list) else []
            caps = node.get("capabilities") if isinstance(node.get("capabilities"), list) else []
            lines.append(
                f"- {node.get('node_id')} {node.get('executor')} / {node.get('runtime_profile')} "
                f"deps={', '.join(str(item) for item in deps) if deps else '-'} "
                f"risk={node.get('risk_level')} cost={node.get('estimated_cost')} "
                f"caps={', '.join(str(item) for item in caps[:4])}"
            )
        card = ActionCard(
            self.scroll.body,
            "Planning",
            "\n".join(lines),
            "Fonte: Universal Task Session / mobile view-model",
        )
        card.pack(fill="x", padx=8, pady=4)
        RawCollapsible(self.scroll.body, lambda item=report: item).pack(fill="x", padx=8, pady=4)
        self._render_mobile_cards(result.data)

    def _render_mobile_cards(self, payload: dict) -> None:
        for card_payload in self.mapper.mobile_cards(payload):
            if str(card_payload.get("card_type") or "") != "execution_plan":
                continue
            TextCard(
                self.scroll.body,
                str(card_payload.get("title") or "Execution Plan"),
                self.mapper.card_summary(card_payload),
                f"mobile card_id={card_payload.get('card_id')}",
                height=4,
            ).pack(fill="x", padx=8, pady=4)

    def _planning_report_from_payload(self, payload: dict) -> dict:
        for card in self.mapper.mobile_cards(payload):
            metadata = card.get("metadata") if isinstance(card.get("metadata"), dict) else {}
            report = metadata.get("planning_report")
            if isinstance(report, dict):
                return report
        return {}
