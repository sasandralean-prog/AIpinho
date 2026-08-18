from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

from apps.launcher.ui.components.component_base import ActionCard, COLORS, NeonButton, ScrollableFrame, TextCard
from apps.launcher.ui.utils.safe_filename import safe_filename


class AgentConsoleTab(ttk.Frame):
    POLL_INTERVAL_MS = 5000

    def __init__(self, parent, client) -> None:
        super().__init__(parent)
        self.client = client
        self.poll_job: str | None = None
        self.configure(style="TFrame")
        bar = tk.Frame(self, background=COLORS["background"])
        bar.pack(fill="x", padx=8, pady=8)
        NeonButton(bar, "Atualizar", command=self.refresh).pack(side="left")
        NeonButton(bar, "Status leve", command=self.refresh, accent=COLORS["green"]).pack(side="left", padx=5)
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self) -> None:
        self._clear()
        self._render_agent_console()
        self._render_bridge_monitor()
        self._render_artifact_center()
        self._render_trace_center()
        self._render_approval_center()
        self._render_locks()

    def _render_agent_console(self) -> None:
        status = self.client.bridge_status()
        if not status.ok:
            TextCard(self.scroll.body, "Agent Console", str(status.error), "Fonte: /api/v1/agent-bridge/status", height=4).pack(fill="x", padx=8, pady=6)
            return
        payload = status.data
        summary = (
            f"bridge_tasks={payload.get('active_bridge_tasks', 0)} "
            f"approvals={payload.get('pending_approvals', 0)} "
            f"artifacts={payload.get('recent_artifacts', 0)} "
            f"locks={payload.get('active_locks', 0)}"
        )
        TextCard(self.scroll.body, "Agent Console", summary, "Status leve; sem diagnostico profundo automatico.", height=3).pack(fill="x", padx=8, pady=6)
        for agent in payload.get("agents", []):
            if not isinstance(agent, dict):
                continue
            card = ActionCard(
                self.scroll.body,
                str(agent.get("display_name") or agent.get("agent_id")),
                f"status={agent.get('status', 'unknown')} sessions={agent.get('session_count', 0)} runs={agent.get('run_count', 0)}",
                f"agent_id={agent.get('agent_id')} active_run={agent.get('active_run_id') or '-'} approvals={agent.get('pending_approvals', 0)}",
            )
            card.pack(fill="x", padx=8, pady=4)

    def _render_bridge_monitor(self) -> None:
        result = self.client.bridge_active()
        rows = result.data.get("bridge_tasks", []) if result.ok else []
        TextCard(self.scroll.body, "Bridge Monitor", f"{len(rows)} bridge tasks ativas.", "Fonte: /api/v1/agent-bridge/active", height=2).pack(fill="x", padx=8, pady=6)
        for item in rows[:12]:
            if not isinstance(item, dict):
                continue
            bridge_id = str(item.get("bridge_task_id") or item.get("delegation_id") or "")
            card = ActionCard(
                self.scroll.body,
                f"{item.get('source_agent')} -> {item.get('target_agent')}",
                str(item.get("prompt_summary") or ""),
                f"status={item.get('status')} bridge_task_id={bridge_id} workspace={item.get('workspace') or '-'}",
            )
            NeonButton(card.actions, "Detalhes", command=lambda bid=bridge_id: self._show_bridge_details(bid)).pack(side="left")
            NeonButton(card.actions, "Copiar IDs", command=lambda data=item: self._copy(str(data))).pack(side="left", padx=5)
            if item.get("status") in {"created", "accepted", "running", "approval_required"}:
                NeonButton(card.actions, "Cancelar", command=lambda bid=bridge_id: self._action_and_refresh(self.client.bridge_cancel, bid), accent=COLORS["pink"]).pack(side="left", padx=5)
            card.pack(fill="x", padx=8, pady=4)

    def _render_artifact_center(self) -> None:
        result = self.client.artifacts()
        rows = result.data.get("artifacts", []) if result.ok else []
        TextCard(self.scroll.body, "Artifact Center", f"{len(rows)} artifacts recentes.", "Fonte: /api/v1/artifacts", height=2).pack(fill="x", padx=8, pady=6)
        for item in rows[:20]:
            if not isinstance(item, dict):
                continue
            artifact_id = str(item.get("artifact_id") or "")
            status = str(item.get("status") or "unknown")
            validation = str(item.get("validation_status") or "unknown")
            card = ActionCard(
                self.scroll.body,
                str(item.get("filename") or artifact_id),
                f"source={item.get('source_agent') or item.get('agent_id') or '-'} task={item.get('owner_task_id') or item.get('run_id') or '-'} bridge={item.get('bridge_task_id') or '-'}",
                f"status={status} validation={validation} type={item.get('content_type') or '-'} size={item.get('size_bytes') or item.get('size') or 0} artifact_id={artifact_id}",
            )
            NeonButton(card.actions, "Revalidar", command=lambda aid=artifact_id: self._action_and_refresh(self.client.artifact_revalidate, aid)).pack(side="left")
            NeonButton(card.actions, "Provenance", command=lambda aid=artifact_id: self._show_artifact_provenance(aid)).pack(side="left", padx=5)
            NeonButton(card.actions, "Baixar", command=lambda data=item: self._download_artifact(data), accent=COLORS["green"]).pack(side="left", padx=5)
            NeonButton(card.actions, "Copiar ID", command=lambda aid=artifact_id: self._copy(aid)).pack(side="left", padx=5)
            if item.get("local_path"):
                NeonButton(card.actions, "Abrir pasta", command=lambda path=str(item.get("local_path")): self._open_artifact_folder(path)).pack(side="left", padx=5)
                NeonButton(card.actions, "Copiar caminho", command=lambda path=str(item.get("local_path")): self._copy(path)).pack(side="left", padx=5)
            card.pack(fill="x", padx=8, pady=4)

    def _render_trace_center(self) -> None:
        result = self.client.traces_recent()
        rows = result.data.get("traces", []) if result.ok else []
        TextCard(
            self.scroll.body,
            "Trace Center",
            f"{len(rows)} traces recentes.",
            "Fonte: /api/v1/debugger/recent; raw oculto por padrao.",
            height=2,
        ).pack(fill="x", padx=8, pady=6)
        for item in rows[:12]:
            if not isinstance(item, dict):
                continue
            trace_id = str(item.get("run_id") or item.get("trace_id") or item.get("bridge_task_id") or "")
            bridge_id = str(item.get("bridge_task_id") or "")
            source = str(item.get("source_agent") or item.get("agent_id") or "-")
            target = str(item.get("target_agent") or item.get("executor_agent") or "-")
            card = ActionCard(
                self.scroll.body,
                f"Trace {source} -> {target}",
                f"status={item.get('status', 'unknown')} operation={item.get('operation_type') or item.get('intent_type') or '-'}",
                f"trace_id={trace_id or '-'} bridge={bridge_id or '-'} task={item.get('task_id') or item.get('run_id') or '-'} artifacts={len(item.get('artifacts') or [])}",
            )
            if bridge_id:
                NeonButton(card.actions, "Bridge trace", command=lambda bid=bridge_id: self._show_bridge_trace(bid)).pack(side="left")
            if trace_id:
                NeonButton(card.actions, "Exportar", command=lambda tid=trace_id: self._export_trace(tid), accent=COLORS["green"]).pack(side="left", padx=5)
                NeonButton(card.actions, "Copiar trace", command=lambda tid=trace_id: self._copy(tid)).pack(side="left", padx=5)
            card.pack(fill="x", padx=8, pady=4)
    def _render_approval_center(self) -> None:
        result = self.client.approvals_pending()
        rows = result.data.get("approvals", []) if result.ok else []
        TextCard(self.scroll.body, "Approval Center", f"{len(rows)} approvals pendentes.", "Fonte: /api/v1/approvals/pending", height=2).pack(fill="x", padx=8, pady=6)
        for item in rows[:20]:
            if not isinstance(item, dict):
                continue
            approval_id = str(item.get("approval_id") or "")
            actions = ", ".join(str(action) for action in item.get("actions_requested", []))
            card = ActionCard(
                self.scroll.body,
                f"Approval {approval_id}",
                f"actions={actions or '-'} reason={item.get('reason') or '-'}",
                f"risk={item.get('risk_level') or '-'} status={item.get('status')} preview={item.get('preview_id') or '-'}",
            )
            NeonButton(card.actions, "Aprovar", command=lambda aid=approval_id: self._action_and_refresh(self.client.approve, aid), accent=COLORS["green"]).pack(side="left")
            NeonButton(card.actions, "Negar", command=lambda aid=approval_id: self._action_and_refresh(self.client.deny, aid), accent=COLORS["pink"]).pack(side="left", padx=5)
            NeonButton(card.actions, "Preview", command=lambda data=item: self._show_approval_preview(data)).pack(side="left", padx=5)
            bridge_task_id = str(item.get("bridge_task_id") or item.get("delegation_id") or "")
            if bridge_task_id:
                NeonButton(card.actions, "Cancelar task", command=lambda bid=bridge_task_id: self._action_and_refresh(self.client.bridge_cancel, bid), accent=COLORS["pink"]).pack(side="left", padx=5)
            NeonButton(card.actions, "Copiar ID", command=lambda aid=approval_id: self._copy(aid)).pack(side="left", padx=5)
            card.pack(fill="x", padx=8, pady=4)

    def _render_locks(self) -> None:
        result = self.client.locks()
        rows = result.data.get("locks", []) if result.ok else []
        TextCard(self.scroll.body, "Workspace Locks", f"{len(rows)} locks ativos.", "Fonte: /api/v1/locks", height=2).pack(fill="x", padx=8, pady=6)
        for item in rows[:20]:
            if not isinstance(item, dict):
                continue
            lock_id = str(item.get("lock_id") or "")
            card = ActionCard(
                self.scroll.body,
                f"Lock {item.get('scope') or 'workspace'}",
                f"workspace={item.get('workspace') or '-'} paths={', '.join(item.get('locked_paths') or [])}",
                f"owner={item.get('owner_agent')} task={item.get('owner_task_id') or '-'} bridge={item.get('bridge_task_id') or '-'} status={item.get('status')} lock_id={lock_id}",
            )
            NeonButton(card.actions, "Liberar", command=lambda lid=lock_id: self._action_and_refresh(self.client.release_lock, lid)).pack(side="left")
            NeonButton(card.actions, "Override", command=lambda lid=lock_id: self._action_and_refresh(self.client.override_lock, lid), accent=COLORS["pink"]).pack(side="left", padx=5)
            NeonButton(card.actions, "Copiar ID", command=lambda lid=lock_id: self._copy(lid)).pack(side="left", padx=5)
            card.pack(fill="x", padx=8, pady=4)

    def _show_bridge_trace(self, bridge_task_id: str) -> None:
        result = self.client.trace_by_bridge_task(bridge_task_id)
        TextCard(self.scroll.body, "Bridge Trace", str(result.data if result.ok else result.error), f"bridge_task_id={bridge_task_id}", height=10).pack(fill="x", padx=8, pady=4)

    def _export_trace(self, trace_id: str) -> None:
        result = self.client.trace_export(trace_id)
        payload = result.data.get("result", result.data) if result.ok and isinstance(result.data, dict) else result.error
        TextCard(self.scroll.body, "Trace Export", str(payload), f"trace_id={trace_id}", height=8).pack(fill="x", padx=8, pady=4)
    def _show_bridge_details(self, bridge_task_id: str) -> None:
        result = self.client.bridge_details(bridge_task_id)
        TextCard(self.scroll.body, "Bridge Details", str(result.data if result.ok else result.error), f"bridge_task_id={bridge_task_id}", height=10).pack(fill="x", padx=8, pady=4)

    def _show_artifact_provenance(self, artifact_id: str) -> None:
        result = self.client.artifact_provenance(artifact_id)
        TextCard(self.scroll.body, "Artifact Provenance", str(result.data if result.ok else result.error), f"artifact_id={artifact_id}", height=8).pack(fill="x", padx=8, pady=4)

    def _show_approval_preview(self, approval: dict[str, object]) -> None:
        summary = {
            "approval_id": approval.get("approval_id"),
            "preview_id": approval.get("preview_id"),
            "requested_action": approval.get("requested_action") or approval.get("actions_requested"),
            "policy_reason": approval.get("policy_reason") or approval.get("reason"),
            "risk_level": approval.get("risk_level"),
            "task_id": approval.get("task_id"),
            "bridge_task_id": approval.get("bridge_task_id") or approval.get("delegation_id"),
        }
        TextCard(self.scroll.body, "Approval Preview", str(summary), "Resumo sanitizado; raw oculto.", height=8).pack(fill="x", padx=8, pady=4)

    def _download_artifact(self, artifact: dict[str, object]) -> None:
        artifact_id = str(artifact.get("artifact_id") or "")
        if not artifact_id:
            return
        filename = safe_filename(str(artifact.get("filename") or f"{artifact_id}.bin"))
        target_name = filedialog.asksaveasfilename(initialfile=filename, title="Salvar artifact")
        if not target_name:
            return
        result = self.client.artifact_download(artifact_id, str(artifact.get("download_endpoint") or ""))
        ok = self.client.save_download(result, Path(target_name))
        summary = f"Download concluido em {target_name}" if ok else f"Falha no download: {result.error or result.status_code}"
        TextCard(self.scroll.body, "Download", summary, f"artifact_id={artifact_id}", height=4).pack(fill="x", padx=8, pady=4)

    def _open_artifact_folder(self, local_path: str) -> None:
        path = Path(local_path)
        folder = path if path.is_dir() else path.parent
        if not folder.exists():
            TextCard(self.scroll.body, "Abrir pasta", "Pasta do artifact nao encontrada.", f"path={local_path}", height=3).pack(fill="x", padx=8, pady=4)
            return
        os.startfile(str(folder))

    def _action_and_refresh(self, method, item_id: str) -> None:
        if not item_id:
            return
        result = method(item_id)
        TextCard(self.scroll.body, "Acao", str(result.data if result.ok else result.error), f"id={item_id}", height=4).pack(fill="x", padx=8, pady=4)
        self.after(300, self.refresh)

    def _copy(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    def _clear(self) -> None:
        for child in self.scroll.body.winfo_children():
            child.destroy()

    def _start_polling(self) -> None:
        self._stop_polling()
        self.poll_job = self.after(self.POLL_INTERVAL_MS, self._poll)

    def _stop_polling(self) -> None:
        if self.poll_job:
            self.after_cancel(self.poll_job)
            self.poll_job = None

    def _poll(self) -> None:
        if self.winfo_ismapped():
            self.refresh()
        self.poll_job = self.after(self.POLL_INTERVAL_MS, self._poll)

    def activate(self) -> None:
        self.refresh()
        self._start_polling()

    def deactivate(self) -> None:
        self._stop_polling()


