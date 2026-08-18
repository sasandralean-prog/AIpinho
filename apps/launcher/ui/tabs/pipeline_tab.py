from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from apps.launcher.ui.components.component_base import ActionCard, COLORS, NeonButton, RawCollapsible, ScrollableFrame, TextCard
from apps.launcher.ui.presentation import PipelinePresentationMapper


class PipelineTab(ttk.Frame):
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
            TextCard(self.scroll.body, "Pipeline", str(result.error or result.data), "Fonte: mobile view-model", height=4).pack(fill="x", padx=8, pady=4)
            self._render_standalone_approvals({})
            return
        payload = result.data
        task = self.mapper.mobile_task(payload)
        approval = self.mapper.mobile_selected_approval(payload)
        self._render_unified_summary(task, approval)
        self._render_execution_graph(payload, task.task_id)
        if approval is not None:
            self._render_selected_approval(approval)
        else:
            TextCard(self.scroll.body, "Approval selecionado", "Nenhum approval selecionado pelo view-model mobile.", height=2).pack(fill="x", padx=8, pady=4)
        self._render_mobile_cards(payload)
        pending = self.pipeline_client.pending_approvals()
        self._render_standalone_approvals(pending.data if pending.ok and isinstance(pending.data, dict) else {})

    def _render_unified_summary(self, task, approval) -> None:
        summary = (
            f"Task selecionada: {task.task_id or 'vazio'}\n"
            f"Approval selecionado: {(approval.approval_id if approval else None) or 'nenhum'}\n"
            f"Tipo de approval: {(approval.approval_kind if approval else task.approval_kind) or '-'}\n"
            f"Task vinculada ao approval: {(approval.linked_task_run_id if approval else task.linked_task_run_id) or '-'}\n"
            f"Fila total: {task.queue_total}\n"
            f"Tasks exigindo decisao: {task.queue_requires_decision}\n"
            f"Approvals de task pendentes: {task.task_approvals_pending}\n"
            f"Approvals avulsos pendentes: {task.standalone_approvals_pending}"
        )
        card = ActionCard(self.scroll.body, task.title, summary, f"status={task.status}")
        if task.task_id:
            NeonButton(card.actions, "Cancelar task", command=lambda item=task.task_id: self._cancel_task(item), accent=COLORS["pink"]).pack(side="left")
            if task.linked_task_run_id:
                NeonButton(card.actions, "Aprovar seguras", command=lambda item=task.linked_task_run_id: self._safe_batch(item, approve=True), accent=COLORS["green"]).pack(side="left", padx=6)
                NeonButton(card.actions, "Negar seguras", command=lambda item=task.linked_task_run_id: self._safe_batch(item, approve=False), accent=COLORS["pink"]).pack(side="left")
        else:
            tk.Label(card.actions, text="Sem task selecionada", background=COLORS["card"], foreground=COLORS["cyan_muted"]).pack(side="left")
        card.pack(fill="x", padx=8, pady=4)
        RawCollapsible(self.scroll.body, lambda text=task.details: text).pack(fill="x", padx=8, pady=4)

    def _render_execution_graph(self, payload: dict, task_id: str | None) -> None:
        graph = self._execution_graph_from_payload(payload)
        if not graph or graph.get("status") == "none":
            TextCard(
                self.scroll.body,
                "Execution Graph",
                "Nenhum grafo cooperativo selecionado pelo view-model mobile.",
                "Fonte: task_run.execution_graph",
                height=3,
            ).pack(fill="x", padx=8, pady=4)
            return
        nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
        edges = graph.get("edges") if isinstance(graph.get("edges"), list) else []
        lines = [
            f"Graph: {graph.get('graph_id')}",
            f"Tipo: {graph.get('graph_type')} | status: {graph.get('status')}",
            f"Nodes: {len(nodes)} | Edges: {len(edges)}",
            f"Ready: {len(graph.get('ready_nodes') or [])} | Running: {len(graph.get('running_nodes') or [])} | Completed: {len(graph.get('completed_nodes') or [])}",
            f"Blocked: {len(graph.get('blocked_nodes') or [])} | Failed: {len(graph.get('failed_nodes') or [])}",
            "",
            "Pipeline:",
        ]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            deps = node.get("dependencies") if isinstance(node.get("dependencies"), list) else []
            lines.append(
                f"- {node.get('node_id')} [{node.get('status')}] "
                f"{node.get('executor')} / {node.get('runtime_profile')} "
                f"deps={', '.join(str(item) for item in deps) if deps else '-'} "
                f"retry={node.get('retry_count') or 0}"
            )
        card = ActionCard(
            self.scroll.body,
            "Execution Graph",
            "\n".join(lines),
            f"graph_id={graph.get('graph_id')} source=mobile view-model",
        )
        if task_id:
            first_retryable = self._first_retryable_node(nodes)
            if first_retryable:
                NeonButton(
                    card.actions,
                    "Retry Node",
                    command=lambda item=task_id, node=first_retryable: self._retry_node(item, node),
                    accent=COLORS["green"],
                ).pack(side="left")
                NeonButton(
                    card.actions,
                    "Cancel Node",
                    command=lambda item=task_id, node=first_retryable: self._cancel_node(item, node),
                    accent=COLORS["pink"],
                ).pack(side="left", padx=6)
        card.pack(fill="x", padx=8, pady=4)
        RawCollapsible(self.scroll.body, lambda item=graph: item).pack(fill="x", padx=8, pady=4)

    def _render_selected_approval(self, approval) -> None:
        meta = f"kind={approval.approval_kind or '-'} linked_task_run_id={approval.linked_task_run_id or '-'} status={approval.status}"
        card = ActionCard(self.scroll.body, approval.title, approval.summary, meta)
        NeonButton(card.actions, "Aprovar", command=lambda item=approval.approval_id: self._decide("approve", item), accent=COLORS["green"]).pack(side="left")
        NeonButton(card.actions, "Negar", command=lambda item=approval.approval_id: self._decide("reject", item), accent=COLORS["pink"]).pack(side="left", padx=6)
        NeonButton(card.actions, "Cancelar", command=lambda item=approval.approval_id: self._decide("cancel", item), accent=COLORS["cyan"]).pack(side="left")
        if approval.linked_task_run_id:
            NeonButton(card.actions, "Aprovar seguras", command=lambda item=approval.linked_task_run_id: self._safe_batch(item, approve=True), accent=COLORS["green"]).pack(side="left", padx=6)
            NeonButton(card.actions, "Negar seguras", command=lambda item=approval.linked_task_run_id: self._safe_batch(item, approve=False), accent=COLORS["pink"]).pack(side="left")
        card.pack(fill="x", padx=8, pady=4)
        RawCollapsible(self.scroll.body, lambda text=approval.details: text).pack(fill="x", padx=8, pady=4)

    def _render_mobile_cards(self, payload: dict) -> None:
        cards = self.mapper.mobile_cards(payload)
        if not cards:
            TextCard(self.scroll.body, "Cards mobile", "Nenhum card retornado pelo view-model mobile.", height=2).pack(fill="x", padx=8, pady=4)
            return
        for card_payload in cards:
            title = str(card_payload.get("title") or card_payload.get("card_id") or "Card")
            status = str(card_payload.get("status") or "unknown")
            card_type = str(card_payload.get("card_type") or "unknown")
            TextCard(
                self.scroll.body,
                title,
                self.mapper.card_summary(card_payload),
                f"mobile card_type={card_type} status={status}",
                height=4,
            ).pack(fill="x", padx=8, pady=4)
            RawCollapsible(self.scroll.body, lambda item=card_payload: item).pack(fill="x", padx=8, pady=4)

    def _execution_graph_from_payload(self, payload: dict) -> dict:
        for card in self.mapper.mobile_cards(payload):
            metadata = card.get("metadata") if isinstance(card.get("metadata"), dict) else {}
            graph = metadata.get("execution_graph")
            if isinstance(graph, dict):
                return graph
        return {}

    @staticmethod
    def _first_retryable_node(nodes: list) -> str | None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if str(node.get("status") or "") in {"failed", "blocked", "cancelled", "completed"}:
                node_id = str(node.get("node_id") or "")
                if node_id:
                    return node_id
        for node in nodes:
            if isinstance(node, dict):
                node_id = str(node.get("node_id") or "")
                if node_id:
                    return node_id
        return None

    def _render_standalone_approvals(self, payload: dict) -> None:
        approvals = self.mapper.standalone_approvals(payload)
        header = TextCard(
            self.scroll.body,
            "Approvals avulsos",
            f"{len(approvals)} approvals pendentes sem task/run vinculada.",
            "Separados da fila de tasks; fonte auxiliar: /api/v1/approvals/pending",
            height=2,
        )
        header.pack(fill="x", padx=8, pady=4)
        for approval in approvals:
            card = ActionCard(self.scroll.body, approval.title, approval.summary, f"status={approval.status} kind={approval.approval_kind or '-'}")
            NeonButton(card.actions, "Aprovar", command=lambda item=approval.approval_id: self._decide("approve", item), accent=COLORS["green"]).pack(side="left")
            NeonButton(card.actions, "Negar", command=lambda item=approval.approval_id: self._decide("reject", item), accent=COLORS["pink"]).pack(side="left", padx=6)
            NeonButton(card.actions, "Cancelar", command=lambda item=approval.approval_id: self._decide("cancel", item), accent=COLORS["cyan"]).pack(side="left")
            card.pack(fill="x", padx=8, pady=4)
            RawCollapsible(self.scroll.body, lambda text=approval.details: text).pack(fill="x", padx=8, pady=4)

    def _decide(self, action: str, approval_id: str | None) -> None:
        if not approval_id:
            return
        method = {"approve": self.pipeline_client.approve, "reject": self.pipeline_client.reject, "cancel": self.pipeline_client.cancel}[action]
        result = method(approval_id)
        TextCard(self.scroll.body, "Approval", str(result.data if result.ok else result.error), f"approval_id={approval_id}", height=3).pack(fill="x", padx=8, pady=4)
        self.refresh()

    def _safe_batch(self, task_id: str, *, approve: bool) -> None:
        result = self.pipeline_client.approve_safe_batch(task_id) if approve else self.pipeline_client.deny_safe_batch(task_id)
        TextCard(self.scroll.body, "Approval batch", str(result.data if result.ok else result.error), f"task_id={task_id}", height=3).pack(fill="x", padx=8, pady=4)
        self.refresh()

    def _cancel_task(self, task_id: str) -> None:
        result = self.pipeline_client.cancel_task(task_id)
        TextCard(self.scroll.body, "Task cancel", str(result.data if result.ok else result.error), f"task_id={task_id}", height=3).pack(fill="x", padx=8, pady=4)
        self.refresh()

    def _retry_node(self, task_id: str, node_id: str) -> None:
        result = self.pipeline_client.retry_node(task_id, node_id)
        TextCard(self.scroll.body, "Retry Node", str(result.data if result.ok else result.error), f"task_id={task_id} node_id={node_id}", height=3).pack(fill="x", padx=8, pady=4)
        self.refresh()

    def _cancel_node(self, task_id: str, node_id: str) -> None:
        result = self.pipeline_client.cancel_node(task_id, node_id)
        TextCard(self.scroll.body, "Cancel Node", str(result.data if result.ok else result.error), f"task_id={task_id} node_id={node_id}", height=3).pack(fill="x", padx=8, pady=4)
        self.refresh()
