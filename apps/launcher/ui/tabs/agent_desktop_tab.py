from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Callable

from apps.launcher.ui.api.agent_api_client import DesktopAgentApiClient
from apps.launcher.ui.components.component_base import (
    COLORS,
    CyberChip,
    FONT_TERMINAL,
    FONT_TITLE,
    NeonButton,
    PlaceholderEntry,
    RoundedSurface,
    ScrollableFrame,
    TextCard,
)


class AgentDesktopTab(ttk.Frame):
    POLL_INTERVAL_MS = 5000

    def __init__(self, parent, client: DesktopAgentApiClient, launcher_state) -> None:
        super().__init__(parent)
        self.client = client
        self.config = client.config
        self.launcher_state = launcher_state
        self.session_id = launcher_state.agent_session(self.config.agent_id)
        self.active_run_id: str | None = None
        self.latest_event_id: str | None = None
        self.display_mode = "normal"
        self.poll_job: str | None = None
        self.last_delegation: dict[str, object] | None = None
        self.configure(style="TFrame")
        self._build()
        self.after_idle(self._ensure_session)

    def _build(self) -> None:
        top = tk.Frame(self, background=COLORS["background"])
        top.pack(fill="x", padx=8, pady=8)
        NeonButton(top, "Sessoes", command=self.open_sessions_dialog).pack(side="left")
        NeonButton(top, "Nova", command=self.create_session, accent=COLORS["green"]).pack(side="left", padx=4)
        NeonButton(top, "Atualizar", command=self.refresh).pack(side="left", padx=4)
        NeonButton(top, "Cancelar run", command=self.cancel_run, accent=COLORS["pink"]).pack(side="left", padx=4)
        self.mode_chips: dict[str, CyberChip] = {}
        for value, label in (("normal", "Normal"), ("details", "Detalhes"), ("raw", "Raw")):
            chip = CyberChip(
                top,
                label,
                command=lambda selected=value: self._set_mode(selected),
                selected=value == self.display_mode,
                width=112,
            )
            chip.pack(side="left", padx=3)
            self.mode_chips[value] = chip

        panes = tk.PanedWindow(
            self,
            orient="horizontal",
            sashwidth=6,
            background=COLORS["cyan"],
            bd=0,
        )
        panes.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        chat_panel = tk.Frame(panes, background=COLORS["background"])
        side_panel = tk.Frame(panes, background=COLORS["background"])
        panes.add(chat_panel, minsize=680, stretch="always")
        panes.add(side_panel, minsize=320)
        self._build_chat(chat_panel)
        self.side_scroll = ScrollableFrame(side_panel)
        self.side_scroll.pack(fill="both", expand=True)

    def _build_chat(self, parent) -> None:
        surface = RoundedSurface(parent, border=COLORS["cyan"], fill=COLORS["terminal"], radius=22)
        surface.pack(fill="both", expand=True)
        header = tk.Frame(surface.inner, background=COLORS["terminal"])
        header.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(
            header,
            text=self.config.display_name,
            background=COLORS["terminal"],
            foreground=COLORS["cyan"],
            font=FONT_TITLE,
        ).pack(side="left")
        for label, color in (
            (self.config.provider_label, COLORS["pink"]),
            ("Governed", COLORS["green"]),
            ("Operator", COLORS["cyan"]),
        ):
            tk.Label(
                header,
                text=label,
                background=COLORS["background"],
                foreground=color,
                padx=10,
                pady=4,
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left", padx=6)
        self.operator_state = tk.Label(
            header,
            text="Idle",
            background=COLORS["terminal"],
            foreground=COLORS["green"],
            font=("Segoe UI", 10, "bold"),
        )
        self.operator_state.pack(side="right", padx=6)

        toolbar = tk.Frame(surface.inner, background=COLORS["terminal"])
        toolbar.pack(fill="x", padx=10, pady=(0, 4))
        NeonButton(toolbar, "Copiar conversa", command=self.copy_conversation).pack(side="left", padx=(0, 6))
        NeonButton(toolbar, "Exportar", command=self.export_conversation).pack(side="left", padx=(0, 6))
        NeonButton(toolbar, "Limpar tela", command=self._clear_chat, accent=COLORS["pink"]).pack(side="left", padx=(0, 6))
        NeonButton(toolbar, "Expandir", command=self.expand_conversation).pack(side="left", padx=(0, 6))
        self.search_input = PlaceholderEntry(toolbar, "Buscar na conversa", font=("Segoe UI", 10), background=COLORS["card"])
        self.search_input.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=5)
        NeonButton(toolbar, "Buscar", command=self.search_conversation).pack(side="left")
        self.new_message_notice = tk.Label(
            toolbar,
            text="",
            background=COLORS["terminal"],
            foreground=COLORS["pink"],
            font=("Segoe UI", 10, "bold"),
        )
        self.new_message_notice.pack(side="right", padx=8)

        terminal = tk.Frame(surface.inner, background=COLORS["terminal"])
        terminal.pack(fill="both", expand=True, padx=10, pady=6)
        self.chat_text = tk.Text(
            terminal,
            wrap="word",
            background=COLORS["terminal"],
            foreground=COLORS["green"],
            insertbackground=COLORS["cyan"],
            selectbackground="#16394A",
            selectforeground=COLORS["white"],
            relief="flat",
            padx=12,
            pady=12,
            font=FONT_TERMINAL,
        )
        self.chat_text.tag_configure("user", foreground=COLORS["green"], spacing1=4, spacing3=10)
        self.chat_text.tag_configure("agent", foreground=COLORS["cyan"], spacing1=4, spacing3=10)
        self.chat_text.tag_configure("event", foreground=COLORS["pink"], spacing1=4, spacing3=8)
        self.chat_text.bind("<MouseWheel>", self._scroll_chat_text)
        self.chat_text.bind("<Button-4>", self._scroll_chat_text)
        self.chat_text.bind("<Button-5>", self._scroll_chat_text)
        scrollbar = tk.Scrollbar(
            terminal,
            command=self.chat_text.yview,
            background=COLORS["cyan"],
            activebackground=COLORS["green"],
            troughcolor=COLORS["terminal"],
            width=10,
            relief="flat",
        )
        self.chat_text.configure(yscrollcommand=scrollbar.set)
        self.chat_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        composer = tk.Frame(surface.inner, background=COLORS["terminal"])
        composer.pack(fill="x", padx=10, pady=(0, 10))
        self.workspace_input = PlaceholderEntry(
            composer,
            f"Workspace autorizado opcional para {self.config.display_name}",
            font=("Segoe UI", 11),
        )
        self.workspace_input.pack(fill="x", pady=(0, 6), ipady=6)
        self.prompt_input = PlaceholderEntry(
            composer,
            f"Mensagem para {self.config.display_name}",
            font=("Segoe UI", 12),
        )
        self.prompt_input.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=8)
        self.prompt_input.bind("<Return>", lambda _event: self.send())
        NeonButton(composer, "Enviar", command=self.send, accent=COLORS["green"]).pack(side="left")
        if self.config.supports_plan:
            NeonButton(composer, "Plano", command=self.plan).pack(side="left", padx=5)
        if self.config.supports_preview:
            NeonButton(composer, "Preview", command=self.preview, accent=COLORS["pink"]).pack(side="left")
        if self.config.supports_route_preview:
            NeonButton(composer, "Ver rota", command=self.route_preview).pack(side="left", padx=5)

    def _ensure_session(self) -> None:
        sessions = self._session_rows()
        ids = {str(item.get("session_id")) for item in sessions}
        if self.session_id not in ids:
            self.session_id = str(sessions[0].get("session_id")) if sessions else None
        if not self.session_id:
            self.create_session()
            return
        self._remember_session()
        self.refresh()

    def create_session(self) -> None:
        result = self.client.create_session()
        if result.ok:
            self.session_id = str(result.data["session"]["session_id"])
            self.latest_event_id = None
            self.active_run_id = None
            self._remember_session()
        self.refresh()

    def open_sessions_dialog(self) -> None:
        sessions = self._session_rows()
        dialog = tk.Toplevel(self)
        dialog.title(f"Sessoes {self.config.display_name}")
        dialog.configure(background=COLORS["background"])
        dialog.transient(self.winfo_toplevel())
        dialog.geometry("760x470")
        dialog.minsize(620, 360)
        surface = RoundedSurface(dialog, border=COLORS["cyan"], fill=COLORS["card"], radius=22)
        surface.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(
            surface.inner,
            text=f"Sessoes {self.config.display_name}",
            background=COLORS["card"],
            foreground=COLORS["cyan"],
            font=FONT_TITLE,
        ).pack(anchor="w", padx=10, pady=(8, 4))
        tk.Label(
            surface.inner,
            text="Abra, renomeie ou remova uma conversa persistente.",
            background=COLORS["card"],
            foreground=COLORS["cyan_muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=10, pady=(0, 8))
        list_frame = tk.Frame(surface.inner, background=COLORS["terminal"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=8)
        listbox = tk.Listbox(
            list_frame,
            background=COLORS["terminal"],
            foreground=COLORS["green"],
            selectbackground="#10321A",
            selectforeground=COLORS["green"],
            relief="flat",
            activestyle="none",
            font=FONT_TERMINAL,
        )
        scrollbar = tk.Scrollbar(
            list_frame,
            command=listbox.yview,
            background=COLORS["cyan"],
            activebackground=COLORS["green"],
            troughcolor=COLORS["terminal"],
            width=10,
            relief="flat",
        )
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        for row in sessions:
            listbox.insert("end", self._session_label(row))

        def selected() -> tuple[int, dict[str, object]] | None:
            selection = listbox.curselection()
            if not selection:
                return None
            index = int(selection[0])
            return index, sessions[index]

        def open_selected() -> None:
            item = selected()
            if not item:
                return
            self.session_id = str(item[1].get("session_id"))
            self.latest_event_id = None
            self.active_run_id = None
            self._remember_session()
            dialog.destroy()
            self.refresh()

        def rename_selected() -> None:
            item = selected()
            if not item:
                return
            index, session = item
            self._rename_dialog(
                dialog,
                str(session.get("title") or self.config.display_name),
                lambda title: self._rename_session(session, index, title, listbox),
            )

        def delete_selected() -> None:
            item = selected()
            if not item:
                return
            index, session = item
            self._confirm_dialog(
                dialog,
                "Deletar chat",
                f"Remover '{session.get('title') or session.get('session_id')}' e seu historico?",
                lambda: self._delete_session(session, index, sessions, listbox),
            )

        def create_new() -> None:
            result = self.client.create_session()
            if not result.ok:
                return
            session = dict(result.data.get("session") or {})
            sessions.insert(0, session)
            listbox.insert(0, self._session_label(session))
            listbox.selection_clear(0, "end")
            listbox.selection_set(0)

        buttons = tk.Frame(surface.inner, background=COLORS["card"])
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        NeonButton(buttons, "Abrir chat", command=open_selected, accent=COLORS["green"]).pack(side="left", padx=5)
        NeonButton(buttons, "Nova", command=create_new).pack(side="left", padx=5)
        NeonButton(buttons, "Renomear", command=rename_selected).pack(side="left", padx=5)
        NeonButton(buttons, "Deletar", command=delete_selected, accent=COLORS["pink"]).pack(side="left", padx=5)
        NeonButton(buttons, "Fechar", command=dialog.destroy).pack(side="right", padx=5)

    def _rename_dialog(self, parent, current_title: str, on_save: Callable[[str], None]) -> None:
        dialog = tk.Toplevel(parent)
        dialog.title("Renomear chat")
        dialog.configure(background=COLORS["background"])
        dialog.transient(parent)
        dialog.geometry("520x220")
        surface = RoundedSurface(dialog, border=COLORS["cyan"], fill=COLORS["card"], radius=22)
        surface.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(
            surface.inner,
            text="Renomear chat",
            background=COLORS["card"],
            foreground=COLORS["cyan"],
            font=FONT_TITLE,
        ).pack(anchor="w", padx=10, pady=(10, 6))
        entry = tk.Entry(
            surface.inner,
            background=COLORS["terminal"],
            foreground=COLORS["green"],
            insertbackground=COLORS["cyan"],
            relief="flat",
            font=FONT_TERMINAL,
        )
        entry.insert(0, current_title)
        entry.pack(fill="x", padx=10, pady=8, ipady=8)
        buttons = tk.Frame(surface.inner, background=COLORS["card"])
        buttons.pack(fill="x", padx=10, pady=8)

        def save() -> None:
            title = entry.get().strip()
            if title:
                on_save(title)
            dialog.destroy()

        NeonButton(buttons, "Salvar", command=save, accent=COLORS["green"]).pack(side="left")
        NeonButton(buttons, "Cancelar", command=dialog.destroy).pack(side="left", padx=6)

    def _confirm_dialog(self, parent, title: str, message: str, on_confirm: Callable[[], None]) -> None:
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(background=COLORS["background"])
        dialog.transient(parent)
        dialog.geometry("560x240")
        surface = RoundedSurface(dialog, border=COLORS["pink"], fill=COLORS["card"], radius=22)
        surface.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(
            surface.inner,
            text=title,
            background=COLORS["card"],
            foreground=COLORS["pink"],
            font=FONT_TITLE,
        ).pack(anchor="w", padx=10, pady=(10, 6))
        tk.Label(
            surface.inner,
            text=message,
            wraplength=500,
            justify="left",
            background=COLORS["card"],
            foreground=COLORS["green"],
            font=("Segoe UI", 12),
        ).pack(anchor="w", padx=10, pady=8)
        buttons = tk.Frame(surface.inner, background=COLORS["card"])
        buttons.pack(fill="x", padx=10, pady=8)

        def confirm() -> None:
            dialog.destroy()
            on_confirm()

        NeonButton(buttons, "Confirmar", command=confirm, accent=COLORS["pink"]).pack(side="left")
        NeonButton(buttons, "Cancelar", command=dialog.destroy).pack(side="left", padx=6)

    def _rename_session(self, session, index, title, listbox) -> None:
        result = self.client.rename_session(str(session.get("session_id")), title)
        if not result.ok:
            return
        session.update(result.data.get("session") or {"title": title})
        listbox.delete(index)
        listbox.insert(index, self._session_label(session))
        listbox.selection_set(index)
        self.refresh()

    def _delete_session(self, session, index, sessions, listbox) -> None:
        session_id = str(session.get("session_id"))
        result = self.client.delete_session(session_id)
        if not result.ok:
            return
        sessions.pop(index)
        listbox.delete(index)
        if self.session_id == session_id:
            self.session_id = str(sessions[0].get("session_id")) if sessions else None
            self._remember_session()
        self.refresh()

    def _session_rows(self) -> list[dict[str, object]]:
        result = self.client.sessions()
        if not result.ok:
            return []
        rows = list(result.data.get("sessions") or [])
        rows.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return rows

    def _session_label(self, session: dict[str, object]) -> str:
        return (
            f"{session.get('title') or self.config.display_name} | "
            f"{session.get('status') or 'idle'} | {session.get('session_id')}"
        )

    def send(self) -> None:
        self._send_with(self.client.send)

    def plan(self) -> None:
        self._send_with(self.client.plan)

    def preview(self) -> None:
        self._send_with(self.client.preview)

    def route_preview(self) -> None:
        self._send_with(self.client.route_preview)

    def _send_with(self, method) -> None:
        if not self.session_id:
            self.create_session()
        prompt = self.prompt_input.get_value()
        if not prompt or not self.session_id:
            return
        workspace = self.workspace_input.get_value()
        self.prompt_input.clear()
        result = method(self.session_id, prompt, workspace)
        if not result.ok:
            self._append("event", f"Falha controlada\n{result.error or result.status_code}")
        self.refresh()

    def cancel_run(self) -> None:
        if not self.active_run_id:
            self._append("event", "Nao ha run ativo para cancelar.")
            return
        result = self.client.cancel_run(self.active_run_id)
        if not result.ok:
            self._append("event", f"Cancelamento falhou: {result.error or result.status_code}")
        self.refresh()

    def refresh(self) -> None:
        self._render_side()
        if not self.session_id:
            self._clear_chat()
            self._append("event", "Crie ou selecione uma sessao.")
            return
        result = self.client.view_model(
            self.session_id,
            after_event_id=None,
            mode=self.display_mode,
        )
        if not result.ok:
            messages = self.client.messages(self.session_id)
            self._render_messages((messages.data.get("messages") or []) if messages.ok else [])
            return
        self._render_view_model(result.data)

    def _render_view_model(self, payload: dict[str, object]) -> None:
        self._update_operator_state(payload)
        self.last_delegation = self._delegation_from_payload(payload)
        if self.display_mode == "raw":
            import json

            self._clear_chat()
            self._append("event", json.dumps(payload, ensure_ascii=True, indent=2))
            return
        messages = list(payload.get("messages") or [])
        if not messages and isinstance(payload.get("timeline"), dict):
            messages = list(payload["timeline"].get("messages") or [])
        self._render_messages(messages)
        active_run = payload.get("active_run")
        if isinstance(active_run, dict):
            self.active_run_id = str(active_run.get("run_id") or "") or None
        self.latest_event_id = str(payload.get("latest_event_id") or "") or self.latest_event_id
        if self.display_mode == "details":
            events = list(payload.get("events") or [])
            for event in events:
                if not isinstance(event, dict):
                    continue
                self._append(
                    "event",
                    f"[{event.get('severity') or 'info'}] "
                    f"{event.get('title') or event.get('event_type') or 'evento'}\n"
                    f"{event.get('human_message') or event.get('human_summary') or ''}",
                )

    def _render_messages(self, messages: list[object]) -> None:
        was_at_bottom = self._at_bottom()
        previous_text = self._conversation_text()
        self._clear_chat()
        for item in messages:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "assistant")
            label = "Voce" if role == "user" else ("Erro" if role == "error" else self.config.display_name)
            content = str(
                item.get("content")
                or item.get("content_sanitized")
                or item.get("text")
                or item.get("human_message")
                or item.get("human_summary")
                or item.get("summary")
                or ""
            )
            tag = "user" if role == "user" else ("event" if role in {"error", "system"} else "agent")
            self._append(tag, f"{label}\n{content}", autoscroll=False)
        changed = self._conversation_text() != previous_text
        if was_at_bottom:
            self.chat_text.see("end")
            self.new_message_notice.configure(text="")
        elif changed:
            self.new_message_notice.configure(text="Nova mensagem")

    def _render_side(self) -> None:
        for child in self.side_scroll.body.winfo_children():
            child.destroy()
        health = self.client.health()
        config_status = self.client.config_status()
        TextCard(
            self.side_scroll.body,
            "Estado",
            "\n".join(
                [
                    f"Agente: {self.config.display_name}",
                    f"Backend: {'online' if health.ok else 'indisponivel'}",
                    f"Sessao: {self.session_id or 'nenhuma'}",
                    f"Run: {self.active_run_id or 'nenhum'}",
                    f"Modo: {self.display_mode}",
                    "Polling: Universal Task Session / 5s",
                ]
            ),
            height=7,
        ).pack(fill="x", pady=6)
        if self.config.external_provider_notice:
            TextCard(
                self.side_scroll.body,
                "Provider",
                self.config.external_provider_notice,
                height=4,
            ).pack(fill="x", pady=6)
        TextCard(
            self.side_scroll.body,
            "Delegation Timeline",
            self._delegation_timeline_text(),
            height=8,
        ).pack(fill="x", pady=6)
        if not config_status.ok:
            TextCard(
                self.side_scroll.body,
                "Config",
                f"Indisponivel: {config_status.error or config_status.status_code}",
                height=3,
            ).pack(fill="x", pady=6)

    def _set_mode(self, value: str) -> None:
        self.display_mode = value
        for name, chip in self.mode_chips.items():
            chip.set_selected(name == value)
        self.refresh()

    def _append(self, tag: str, text: str, *, autoscroll: bool = False) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", text.strip() + "\n\n", tag)
        self.chat_text.configure(state="disabled")
        if autoscroll:
            self.chat_text.see("end")

    def _clear_chat(self) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", "end")
        self.chat_text.configure(state="disabled")
        if hasattr(self, "new_message_notice"):
            self.new_message_notice.configure(text="")

    def _at_bottom(self) -> bool:
        return self.chat_text.yview()[1] >= 0.98

    def _scroll_chat_text(self, event) -> str:
        if getattr(event, "num", None) == 4:
            delta = -3
        elif getattr(event, "num", None) == 5:
            delta = 3
        else:
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta:
            self.chat_text.yview_scroll(delta, "units")
            if self._at_bottom() and hasattr(self, "new_message_notice"):
                self.new_message_notice.configure(text="")
        return "break"

    def _conversation_text(self) -> str:
        return self.chat_text.get("1.0", "end-1c")

    def copy_conversation(self) -> None:
        text = self._conversation_text()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.new_message_notice.configure(text="Conversa copiada")

    def export_conversation(self) -> None:
        exports = Path(__file__).resolve().parents[4] / "data" / "runtime" / "operator_exports"
        exports.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = exports / f"{self.config.agent_id}_{stamp}.txt"
        path.write_text(self._conversation_text(), encoding="utf-8")
        self.new_message_notice.configure(text=f"Exportado: {path.name}")

    def expand_conversation(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(f"{self.config.display_name} - conversa")
        dialog.configure(background=COLORS["background"])
        dialog.geometry("980x720")
        surface = RoundedSurface(dialog, border=COLORS["cyan"], fill=COLORS["terminal"], radius=22)
        surface.pack(fill="both", expand=True, padx=12, pady=12)
        text = tk.Text(
            surface.inner,
            wrap="word",
            background=COLORS["terminal"],
            foreground=COLORS["green"],
            selectbackground="#16394A",
            selectforeground=COLORS["white"],
            relief="flat",
            padx=12,
            pady=12,
            font=FONT_TERMINAL,
        )
        text.insert("1.0", self._conversation_text())
        text.pack(fill="both", expand=True, padx=10, pady=10)

    def search_conversation(self) -> None:
        query = self.search_input.get_value()
        self.chat_text.tag_remove("search_hit", "1.0", "end")
        if not query:
            return
        self.chat_text.tag_configure("search_hit", background="#274A16", foreground=COLORS["white"])
        start = "1.0"
        first_hit = None
        while True:
            index = self.chat_text.search(query, start, stopindex="end", nocase=True)
            if not index:
                break
            end = f"{index}+{len(query)}c"
            self.chat_text.tag_add("search_hit", index, end)
            first_hit = first_hit or index
            start = end
        if first_hit:
            self.chat_text.see(first_hit)
            self.new_message_notice.configure(text=f"Busca: {query}")
        else:
            self.new_message_notice.configure(text="Busca sem resultado")

    def _update_operator_state(self, payload: dict[str, object]) -> None:
        state = "Idle"
        active_run = payload.get("active_run")
        if isinstance(active_run, dict):
            status = str(active_run.get("status") or "").lower()
            if status in {"queued", "running", "created"}:
                state = "Polling"
            if active_run.get("delegation_id"):
                state = "Delegando"
            if status in {"waiting_input", "approval_required"}:
                state = "Review"
            if status in {"completed", "partial"}:
                state = "Completed"
        if hasattr(self, "operator_state"):
            self.operator_state.configure(text=state)

    def _delegation_from_payload(self, payload: dict[str, object]) -> dict[str, object] | None:
        delegation = payload.get("delegation")
        if isinstance(delegation, dict):
            return delegation
        active_run = payload.get("active_run")
        if isinstance(active_run, dict):
            nested = active_run.get("delegation")
            if isinstance(nested, dict):
                return nested
            delegation_id = str(active_run.get("delegation_id") or "")
            if delegation_id:
                return {
                    "delegation_id": delegation_id,
                    "executor": active_run.get("executor") or "aipinho",
                    "child_run_id": active_run.get("child_run_id") or "",
                    "polling_count": active_run.get("polling_count") or 0,
                    "review_status": active_run.get("review_status") or "not_started",
                    "evidence_refs": active_run.get("evidence_refs") or [],
                }
        return None

    def _delegation_timeline_text(self) -> str:
        delegation = self.last_delegation or {}
        delegation_id = str(delegation.get("delegation_id") or "")
        if not delegation_id:
            return "Resposta direta do Provider\nSem delegacao"
        evidence = delegation.get("evidence_refs")
        evidence_count = len(evidence) if isinstance(evidence, list) else 0
        return "\n".join(
            [
                f"{self.config.display_name}",
                "Delegou",
                "AIpinho",
                str(delegation.get("executor") or "Executor"),
                "Review",
                "Resposta",
                f"Delegation ID: {delegation_id}",
                f"Child run: {delegation.get('child_run_id') or 'nenhum'}",
                f"Polling: {delegation.get('polling_count') or 0}",
                f"Evidence: {evidence_count}",
                f"Review: {delegation.get('review_status') or 'not_started'}",
            ]
        )

    def _remember_session(self) -> None:
        self.launcher_state.save_agent_session(self.config.agent_id, self.session_id)

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
