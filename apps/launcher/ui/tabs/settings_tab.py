from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any

from apps.launcher.ui.components.component_base import COLORS, NeonButton, ScrollableFrame, TextCard
from apps.launcher.ui.utils.formatting import as_text


class SettingsTab(ttk.Frame):
    def __init__(self, parent, connection_client, event_contract_client, monitor_client, state=None, governance_client=None) -> None:
        super().__init__(parent)
        self.connection_client = connection_client
        self.event_contract_client = event_contract_client
        self.monitor_client = monitor_client
        self.state = state
        self.governance_client = governance_client
        self.last_change_id: str | None = None
        self.last_backup_id: str | None = None
        form = tk.Frame(self, background=COLORS["background"])
        form.pack(fill="x", padx=8, pady=8)
        self.host = tk.Entry(form, width=18, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 12))
        self.host.insert(0, getattr(state, "host", "127.0.0.1"))
        self.host.pack(side="left", padx=(0, 8), ipady=8)
        self.token = tk.Entry(form, width=32, show="*", background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 12))
        if getattr(state, "token", None):
            self.token.insert(0, state.token)
        self.token.pack(side="left", padx=4, ipady=8)
        NeonButton(form, "Salvar perfil", command=self.save_profile).pack(side="left", padx=4)
        NeonButton(form, "Atualizar", command=self.refresh).pack(side="left", padx=4)
        NeonButton(form, "Governanca", command=self.refresh_governance).pack(side="left", padx=4)
        NeonButton(form, "Criar token", command=self.create_token).pack(side="left", padx=4)
        flow_form = tk.Frame(self, background=COLORS["background"])
        flow_form.pack(fill="x", padx=8, pady=(0, 8))
        self.flow_operation = tk.Entry(flow_form, width=22, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 11))
        self.flow_operation.insert(0, "copy_file")
        self.flow_operation.pack(side="left", padx=(0, 6), ipady=6)
        self.flow_source = tk.Entry(flow_form, width=28, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 11))
        self.flow_source.insert(0, "source workspace id")
        self.flow_source.pack(side="left", padx=4, ipady=6)
        self.flow_target = tk.Entry(flow_form, width=28, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 11))
        self.flow_target.insert(0, "target workspace id")
        self.flow_target.pack(side="left", padx=4, ipady=6)
        NeonButton(flow_form, "Preview fluxo", command=self.preview_flow).pack(side="left", padx=4)
        workspace_form = tk.Frame(self, background=COLORS["background"])
        workspace_form.pack(fill="x", padx=8, pady=(0, 8))
        self.workspace_id = tk.Entry(workspace_form, width=20, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 11))
        self.workspace_id.insert(0, "workspace_id")
        self.workspace_id.pack(side="left", padx=(0, 6), ipady=6)
        self.workspace_label = tk.Entry(workspace_form, width=22, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 11))
        self.workspace_label.insert(0, "label")
        self.workspace_label.pack(side="left", padx=4, ipady=6)
        self.workspace_path = tk.Entry(workspace_form, width=48, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 11))
        self.workspace_path.insert(0, "root_path")
        self.workspace_path.pack(side="left", padx=4, ipady=6)
        self.workspace_role = tk.Entry(workspace_form, width=18, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Segoe UI", 11))
        self.workspace_role.insert(0, "target_mutable")
        self.workspace_role.pack(side="left", padx=4, ipady=6)
        NeonButton(workspace_form, "Criar mudanca", command=self.create_workspace_change).pack(side="left", padx=4)
        action_form = tk.Frame(self, background=COLORS["background"])
        action_form.pack(fill="x", padx=8, pady=(0, 8))
        self.permissions_json = tk.Entry(action_form, width=72, background=COLORS["terminal"], foreground=COLORS["green"], insertbackground=COLORS["cyan"], relief="flat", font=("Consolas", 10))
        self.permissions_json.insert(0, '{"read_file":"allowed","list_files":"allowed","create_file":"ask","modify_file":"ask"}')
        self.permissions_json.pack(side="left", padx=(0, 6), ipady=6)
        NeonButton(action_form, "Aprovar ultima", command=self.approve_last_change).pack(side="left", padx=4)
        NeonButton(action_form, "Aplicar ultima", command=self.apply_last_change).pack(side="left", padx=4)
        NeonButton(action_form, "Rollback ultimo", command=self.rollback_last_backup).pack(side="left", padx=4)
        self.scroll = ScrollableFrame(self); self.scroll.pack(fill="both", expand=True)
        self.refresh()

    def save_profile(self) -> None:
        if self.state is None:
            return
        self.state.host = self.host.get().strip() or "127.0.0.1"
        self.state.token = self.token.get().strip() or None
        self.state.save()
        TextCard(self.scroll.body, "Config", "Perfil salvo. A proxima abertura do launcher usa estes valores.", "token protegido no campo local", height=3).pack(fill="x", padx=8, pady=4)

    def create_token(self) -> None:
        self.last_token = self.connection_client.create_token().data
        self.refresh()

    def refresh(self) -> None:
        for child in self.scroll.body.winfo_children(): child.destroy()
        for title, result in [
            ("Perfis", self.connection_client.profiles()),
            ("ADB reverse", self.connection_client.adb_commands()),
            ("Pairing", self.connection_client.pairing_status()),
            ("Recursos", self.monitor_client.resources()),
            ("Event Registry", self.event_contract_client.status()),
            ("Decision Ownership", self.event_contract_client.ownership()),
        ]:
            TextCard(self.scroll.body, title, str(result.data if result.ok else result.error)).pack(fill="x", padx=8, pady=4)
        if hasattr(self, "last_token"):
            TextCard(self.scroll.body, "Token criado (mostrar uma vez)", str(self.last_token)).pack(fill="x", padx=8, pady=4)
        self._render_governance()

    def refresh_governance(self) -> None:
        self.refresh()

    def preview_flow(self) -> None:
        if self.governance_client is None:
            TextCard(self.scroll.body, "Workspace Flow", "GovernanceClient indisponivel.", height=3).pack(fill="x", padx=8, pady=4)
            return
        payload = {
            "operation": self.flow_operation.get().strip() or "copy_file",
            "source": {"workspace_id": self.flow_source.get().strip(), "path": ""},
            "target": {"workspace_id": self.flow_target.get().strip(), "path": ""},
            "requested_by": {"type": "user", "id": "launcher"},
        }
        result = self.governance_client.flow_plan(payload)
        TextCard(self.scroll.body, "Workspace Flow Preview", self._format_result(result.data if result.ok else result.error), height=10).pack(fill="x", padx=8, pady=4)

    def create_workspace_change(self) -> None:
        if self.governance_client is None:
            return
        result = self.governance_client.create_workspace(
            workspace_id=self.workspace_id.get().strip(),
            human_label=self.workspace_label.get().strip(),
            root_path=self.workspace_path.get().strip(),
            role=self.workspace_role.get().strip(),
            permissions=self._permissions_payload(),
        )
        payload = result.data if result.ok else {}
        if isinstance(payload, dict):
            self._remember_change(payload)
        TextCard(self.scroll.body, "Workspace Change Preview", self._format_result(result.data if result.ok else result.error), height=12).pack(fill="x", padx=8, pady=4)

    def approve_last_change(self) -> None:
        if self.governance_client is None or not self.last_change_id:
            TextCard(self.scroll.body, "Config Change", "Nenhuma mudanca selecionada para aprovar.", height=3).pack(fill="x", padx=8, pady=4)
            return
        result = self.governance_client.approve_change(self.last_change_id)
        TextCard(self.scroll.body, "Config Change Approved", self._format_result(result.data if result.ok else result.error), height=8).pack(fill="x", padx=8, pady=4)

    def apply_last_change(self) -> None:
        if self.governance_client is None or not self.last_change_id:
            TextCard(self.scroll.body, "Config Change", "Nenhuma mudanca selecionada para aplicar.", height=3).pack(fill="x", padx=8, pady=4)
            return
        result = self.governance_client.apply_change(self.last_change_id)
        payload = result.data if result.ok else {}
        if isinstance(payload, dict):
            self._remember_backup(payload)
        TextCard(self.scroll.body, "Config Change Applied", self._format_result(result.data if result.ok else result.error), height=10).pack(fill="x", padx=8, pady=4)

    def rollback_last_backup(self) -> None:
        if self.governance_client is None:
            return
        if not self.last_backup_id:
            backups = self.governance_client.backups()
            payload = backups.data if backups.ok else {}
            if isinstance(payload, dict):
                self._remember_backup(payload)
        if not self.last_backup_id:
            TextCard(self.scroll.body, "Rollback", "Nenhum backup selecionado para rollback.", height=3).pack(fill="x", padx=8, pady=4)
            return
        result = self.governance_client.rollback(self.last_backup_id)
        TextCard(self.scroll.body, "Rollback Applied", self._format_result(result.data if result.ok else result.error), height=10).pack(fill="x", padx=8, pady=4)

    def _render_governance(self) -> None:
        if self.governance_client is None:
            return
        sections: list[tuple[str, Any]] = [
            ("Governance Health", self.governance_client.health()),
            ("Effective Policy", self.governance_client.effective_policy()),
            ("Workspaces", self.governance_client.workspaces()),
            ("Permission Matrix", self.governance_client.permission_matrix()),
            ("Flow Rules", self.governance_client.flow_rules()),
            ("Config Changes", self.governance_client.changes()),
            ("Backups / Rollback", self.governance_client.backups()),
        ]
        for title, result in sections:
            payload = result.data if result.ok else result.error
            if isinstance(payload, dict):
                self._remember_change(payload)
                self._remember_backup(payload)
            TextCard(self.scroll.body, title, self._format_result(payload), height=8).pack(fill="x", padx=8, pady=4)

    def _format_result(self, value: Any) -> str:
        if value is None:
            return "Sem dados."
        return as_text(value)

    def _permissions_payload(self) -> dict[str, str]:
        raw = self.permissions_json.get().strip()
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(value, dict):
            return {}
        return {str(key): str(item) for key, item in value.items()}

    def _remember_change(self, payload: dict[str, Any]) -> None:
        change = payload.get("change")
        if isinstance(change, dict) and change.get("change_id"):
            self.last_change_id = str(change["change_id"])
        changes = payload.get("changes")
        if isinstance(changes, list):
            for item in changes:
                if isinstance(item, dict) and item.get("change_id") and item.get("status") != "applied":
                    self.last_change_id = str(item["change_id"])
                    break

    def _remember_backup(self, payload: dict[str, Any]) -> None:
        result = payload.get("result")
        if isinstance(result, dict) and result.get("backup_id"):
            self.last_backup_id = str(result["backup_id"])
        backups = payload.get("backups")
        if isinstance(backups, list) and backups:
            first = backups[0]
            if isinstance(first, dict) and first.get("backup_id"):
                self.last_backup_id = str(first["backup_id"])
