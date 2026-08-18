from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from typing import Callable

from apps.launcher.ui.components.component_base import (
    ActionCard,
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
from apps.launcher.ui.presentation import ArtifactPresentation, ChatPresentationMapper
from apps.launcher.ui.utils.safe_filename import safe_filename


class ChatTab(ttk.Frame):
    def __init__(self, parent, chat_client, artifact_client, launcher_state=None) -> None:
        super().__init__(parent)
        self.chat_client = chat_client
        self.artifact_client = artifact_client
        self.launcher_state = launcher_state
        self.mapper = ChatPresentationMapper()
        self.session_id: str | None = (
            launcher_state.selected_session_id if launcher_state is not None else None
        )
        self.mode_value = "Normal"
        self.speaker_task_id: str | None = None
        self.speaker_cursor: str | None = None
        self.speaker_event_ids: set[str] = set()
        self.speaker_poll_job: str | None = None
        self.configure(style="TFrame")

        top = tk.Frame(self, background=COLORS["background"])
        top.pack(fill="x", padx=8, pady=8)
        NeonButton(top, "Sessoes", command=self.open_sessions_dialog).pack(side="left")
        NeonButton(top, "Nova", command=self.create_session, accent=COLORS["green"]).pack(side="left", padx=4)
        NeonButton(top, "Atualizar", command=self.refresh).pack(side="left", padx=6)
        self.mode_chips: dict[str, CyberChip] = {}
        for label in ("Normal", "Detalhes", "Raw"):
            chip = CyberChip(top, label, command=lambda value=label: self._set_mode(value), selected=label == self.mode_value, width=116)
            chip.pack(side="left", padx=4)
            self.mode_chips[label] = chip

        self.panes = tk.PanedWindow(self, orient="horizontal", sashwidth=6, background=COLORS["cyan"], bd=0)
        self.panes.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.chat_panel = tk.Frame(self.panes, background=COLORS["background"])
        self.details_panel = tk.Frame(self.panes, background=COLORS["background"])
        self.panes.add(self.chat_panel, minsize=680, stretch="always")
        self.panes.add(self.details_panel, minsize=340)

        self._build_chat_terminal()
        self.details_scroll = ScrollableFrame(self.details_panel)
        self.details_scroll.pack(fill="both", expand=True)

        self.refresh()
        self._schedule_speaker_poll()

    def _build_chat_terminal(self) -> None:
        self.chat_surface = RoundedSurface(self.chat_panel, border=COLORS["cyan"], fill=COLORS["terminal"], radius=22)
        self.chat_surface.pack(fill="both", expand=True)
        header = tk.Frame(self.chat_surface.inner, background=COLORS["terminal"])
        header.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(
            header,
            text="AIpinho",
            background=COLORS["terminal"],
            foreground=COLORS["cyan"],
            font=FONT_TITLE,
        ).pack(side="left")
        for label, color in (("Local", COLORS["pink"]), ("Governed", COLORS["green"])):
            tk.Label(
                header,
                text=label,
                background=COLORS["background"],
                foreground=color,
                padx=10,
                pady=4,
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left", padx=6)

        body = tk.Frame(self.chat_surface.inner, background=COLORS["terminal"])
        body.pack(fill="both", expand=True, padx=10, pady=(4, 8))
        self.chat_text = tk.Text(
            body,
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
        self.chat_text.bind("<MouseWheel>", self._scroll_chat_text)
        self.chat_text.bind("<Button-4>", self._scroll_chat_text)
        self.chat_text.bind("<Button-5>", self._scroll_chat_text)
        self.chat_text.tag_configure("assistant", justify="left", foreground=COLORS["green"], lmargin1=8, lmargin2=8, rmargin=90, spacing1=4, spacing3=10)
        self.chat_text.tag_configure("user", justify="left", foreground=COLORS["green"], lmargin1=8, lmargin2=8, rmargin=90, spacing1=4, spacing3=10)
        self.chat_text.tag_configure("system", justify="center", foreground=COLORS["cyan_muted"], spacing1=4, spacing3=8)
        scrollbar = tk.Scrollbar(
            body,
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

        composer = tk.Frame(self.chat_surface.inner, background=COLORS["terminal"])
        composer.pack(fill="x", padx=10, pady=(0, 10))
        self.workspace_input = PlaceholderEntry(
            composer,
            "Workspace autorizado opcional para AIpinho",
            font=("Segoe UI", 11),
        )
        self.workspace_input.pack(fill="x", pady=(0, 6), ipady=6)
        self.input = PlaceholderEntry(
            composer,
            "Mensagem para AIpinho",
            font=("Segoe UI", 12),
        )
        self.input.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=8)
        self.input.bind("<Return>", lambda _event: self.send_message())
        NeonButton(composer, "Enviar", command=self.send_message, accent=COLORS["green"]).pack(side="left")

    def _set_mode(self, value: str) -> None:
        self.mode_value = value
        for label, chip in self.mode_chips.items():
            chip.set_selected(label == value)
        self.refresh()

    def _clear_details(self) -> None:
        for child in self.details_scroll.body.winfo_children():
            child.destroy()

    def _clear_chat(self) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", "end")
        self.chat_text.configure(state="disabled")

    def create_session(self) -> None:
        result = self.chat_client.create_session("Launcher Desktop")
        if result.ok:
            self.session_id = result.data["session"]["session_id"]
            self._remember_session()
        self.refresh()

    def open_sessions_dialog(self) -> None:
        sessions_result = self.chat_client.list_sessions()
        if not sessions_result.ok:
            messagebox.showerror("Sessoes", f"Nao consegui carregar sessoes: {sessions_result.error or sessions_result.status_code}")
            return
        sessions = list(sessions_result.data.get("sessions") or [])
        sessions.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)

        dialog = tk.Toplevel(self)
        dialog.title("Sessoes de chat")
        dialog.configure(background=COLORS["background"])
        dialog.transient(self.winfo_toplevel())
        dialog.geometry("760x460")
        dialog.minsize(620, 360)

        surface = RoundedSurface(dialog, border=COLORS["cyan"], fill=COLORS["card"])
        surface.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(surface.inner, text="Sessoes de chat", background=COLORS["card"], foreground=COLORS["cyan"], font=FONT_TITLE).pack(anchor="w", padx=10, pady=(8, 4))
        tk.Label(
            surface.inner,
            text="Selecione uma conversa para abrir, renomear ou deletar.",
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
        listbox_scrollbar = tk.Scrollbar(
            list_frame,
            command=listbox.yview,
            background=COLORS["cyan"],
            activebackground=COLORS["green"],
            troughcolor=COLORS["terminal"],
            width=10,
            relief="flat",
        )
        listbox.configure(yscrollcommand=listbox_scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        listbox_scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        for session in sessions:
            listbox.insert("end", self._session_dialog_label(session))
        active_index = next((index for index, session in enumerate(sessions) if session.get("session_id") == self.session_id), None)
        if active_index is not None:
            listbox.selection_set(active_index)
            listbox.see(active_index)
        elif sessions:
            listbox.selection_set(0)

        buttons = tk.Frame(surface.inner, background=COLORS["card"])
        buttons.pack(fill="x", padx=10, pady=(0, 10))

        def selected_session() -> dict[str, object] | None:
            selection = listbox.curselection()
            if not selection:
                return None
            return sessions[int(selection[0])]

        def open_selected() -> None:
            session = selected_session()
            if not session:
                messagebox.showinfo("Sessoes", "Selecione uma sessao primeiro.")
                return
            self.session_id = str(session.get("session_id"))
            self._remember_session()
            dialog.destroy()
            self.refresh()

        def rename_selected() -> None:
            session = selected_session()
            if not session:
                messagebox.showinfo("Sessoes", "Selecione uma sessao primeiro.")
                return
            current_title = str(session.get("title") or "")

            def save(new_title: str) -> None:
                result = self.chat_client.rename_session(str(session.get("session_id")), new_title)
                if not result.ok:
                    messagebox.showerror("Renomear chat", f"Nao consegui renomear: {result.error or result.status_code}")
                    return
                session.update(result.data.get("session") or {})
                index = listbox.curselection()[0]
                listbox.delete(index)
                listbox.insert(index, self._session_dialog_label(session))
                listbox.selection_set(index)
                self.refresh()

            self._show_neon_text_dialog(dialog, "Renomear chat", current_title, save)

        def delete_selected() -> None:
            session = selected_session()
            if not session:
                messagebox.showinfo("Sessoes", "Selecione uma sessao primeiro.")
                return
            title = str(session.get("title") or session.get("session_id"))

            def delete_confirmed() -> None:
                result = self.chat_client.delete_session(str(session.get("session_id")))
                if not result.ok:
                    messagebox.showerror("Deletar chat", f"Nao consegui deletar: {result.error or result.status_code}")
                    return
                deleted_id = str(session.get("session_id"))
                index = listbox.curselection()[0]
                listbox.delete(index)
                sessions.pop(index)
                if self.session_id == deleted_id:
                    self.session_id = str(sessions[0].get("session_id")) if sessions else None
                    self._remember_session()
                if sessions:
                    listbox.selection_set(min(index, len(sessions) - 1))
                self.refresh()

            self._show_neon_confirm_dialog(
                dialog,
                "Deletar chat",
                f"Deletar a sessao '{title}' e suas mensagens?",
                delete_confirmed,
            )

        NeonButton(buttons, "Abrir chat", command=open_selected, accent=COLORS["green"]).pack(side="left", padx=6)
        NeonButton(buttons, "Renomear", command=rename_selected).pack(side="left", padx=6)
        NeonButton(buttons, "Deletar", command=delete_selected, accent=COLORS["pink"]).pack(side="left", padx=6)
        NeonButton(buttons, "Fechar", command=dialog.destroy).pack(side="right", padx=6)

    def _session_dialog_label(self, session: dict[str, object]) -> str:
        title = str(session.get("title") or "Nova conversa")
        message_count = int(session.get("message_count") or 0)
        updated_at = str(session.get("updated_at") or "")
        session_id = str(session.get("session_id") or "")
        return f"{title}  |  mensagens: {message_count}  |  atualizada: {updated_at}  |  {session_id}"

    def _show_neon_text_dialog(
        self,
        parent: tk.Misc,
        title: str,
        initial_value: str,
        on_save: Callable[[str], None],
    ) -> None:
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(background=COLORS["background"])
        dialog.transient(parent)
        dialog.geometry("520x220")
        surface = RoundedSurface(dialog, border=COLORS["cyan"], fill=COLORS["card"], radius=22)
        surface.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(
            surface.inner,
            text=title,
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
        entry.insert(0, initial_value)
        entry.pack(fill="x", padx=10, pady=8, ipady=8)
        entry.focus_set()
        entry.selection_range(0, "end")
        buttons = tk.Frame(surface.inner, background=COLORS["card"])
        buttons.pack(fill="x", padx=10, pady=8)

        def save() -> None:
            value = entry.get().strip()
            if not value:
                return
            on_save(value)
            dialog.destroy()

        NeonButton(buttons, "Salvar", command=save, accent=COLORS["green"]).pack(side="left")
        NeonButton(buttons, "Cancelar", command=dialog.destroy).pack(side="left", padx=6)
        entry.bind("<Return>", lambda _event: save())

    def _show_neon_confirm_dialog(
        self,
        parent: tk.Misc,
        title: str,
        message: str,
        on_confirm: Callable[[], None],
    ) -> None:
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

    def send_message(self) -> None:
        if not self.session_id:
            self.create_session()
        content = self.input.get_value()
        if self.session_id and content:
            workspace = self.workspace_input.get_value()
            metadata: dict[str, object] = {}
            if workspace:
                metadata["workspace"] = workspace
            self.chat_client.send_message(self.session_id, content, metadata=metadata)
            self.input.clear()
        self.refresh()

    def _remember_session(self) -> None:
        if self.launcher_state is None:
            return
        self.launcher_state.selected_session_id = self.session_id
        self.launcher_state.save()

    def refresh(self) -> None:
        previous_view = self.chat_text.yview()[0]
        self._clear_details()
        self._clear_chat()
        sessions = self.chat_client.list_sessions()
        if sessions.ok and sessions.data.get("sessions"):
            session_ids = {
                str(session.get("session_id"))
                for session in sessions.data["sessions"]
            }
            if self.session_id not in session_ids:
                self.session_id = str(sessions.data["sessions"][-1]["session_id"])
                self._remember_session()
        session_summary = f"Sessao ativa: {self.session_id or 'nenhuma'}"
        TextCard(self.details_scroll.body, "Estado", session_summary, "modo humano por padrao", height=2).pack(fill="x", padx=8, pady=4)
        if not self.session_id:
            self._insert_system_line("Crie ou envie uma mensagem para iniciar a conversa.")
            return

        timeline = self.chat_client.timeline(self.session_id)
        if not timeline.ok:
            self._insert_system_line("Nao consegui carregar a timeline da conversa.")
            TextCard(self.details_scroll.body, "Timeline", str(timeline.error), height=4).pack(fill="x", padx=8, pady=4)
            return

        presentation = self.mapper.map(timeline.data)
        latest_task_id = next((message.task_id for message in reversed(presentation.messages) if message.task_id), None)
        if latest_task_id != self.speaker_task_id:
            self.speaker_task_id = latest_task_id
            self.speaker_cursor = None
            self.speaker_event_ids.clear()
        self._render_messages(presentation, previous_view=previous_view)
        self._render_timeline_cards(presentation)

    def _schedule_speaker_poll(self) -> None:
        if self.speaker_poll_job is not None:
            self.after_cancel(self.speaker_poll_job)
        self.speaker_poll_job = self.after(5000, self._poll_speaker_updates)

    def _poll_speaker_updates(self) -> None:
        try:
            if self.speaker_task_id:
                result = self.chat_client.speaker_updates(self.speaker_task_id, self.speaker_cursor)
                if result.ok:
                    for message in result.data.get("messages", []):
                        source_ids = [str(item) for item in message.get("source_event_ids", [])]
                        if source_ids and all(item in self.speaker_event_ids for item in source_ids):
                            continue
                        text = str(message.get("text") or "").strip()
                        if text:
                            self.chat_text.configure(state="normal")
                            self.chat_text.insert("end", f"AIpinho\n{text}\n\n", "assistant")
                            self.chat_text.configure(state="disabled")
                        self.speaker_event_ids.update(source_ids)
                    self.speaker_cursor = result.data.get("latest_event_id") or self.speaker_cursor
        finally:
            self._schedule_speaker_poll()

    def destroy(self) -> None:
        if self.speaker_poll_job is not None:
            self.after_cancel(self.speaker_poll_job)
            self.speaker_poll_job = None
        super().destroy()

    def _render_messages(self, presentation, *, previous_view: float = 0.0) -> None:
        if not presentation.messages:
            self._insert_system_line("AIpinho aguardando sua mensagem.")
            return
        self.chat_text.configure(state="normal")
        for message in presentation.messages:
            tag = "user" if message.role == "user" else "assistant"
            speaker = "Voce" if message.role == "user" else "AIpinho"
            self.chat_text.insert("end", f"{speaker}\n{message.text}\n\n", tag)
        self.chat_text.yview_moveto(previous_view)
        self.chat_text.configure(state="disabled")

    def _insert_system_line(self, text: str) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", f"{text}\n", "system")
        self.chat_text.configure(state="disabled")

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
        return "break"

    def _render_timeline_cards(self, presentation) -> None:
        mode = self.mode_value.lower()
        if mode == "detalhes":
            self._render_details(presentation)
        elif mode == "raw":
            TextCard(self.details_scroll.body, "Raw sanitizado", str(presentation.raw_payload), "visivel por acao explicita", height=12).pack(fill="both", padx=8, pady=4)
        else:
            lines = list(presentation.state_lines)
            for message in presentation.messages:
                lines.append(f"{message.label}: {message.safety_label} task={message.task_id or 'sem task'} artifacts={len(message.artifacts)}")
            TextCard(self.details_scroll.body, "Timeline", "\n".join(lines), "log sanitizado abaixo do chat", height=8).pack(fill="both", padx=8, pady=4)
        self._render_artifact_actions(presentation)

    def _render_details(self, presentation) -> None:
        lines: list[str] = []
        for message in presentation.messages:
            details = message.details or ["Nenhum detalhe tecnico relevante para esta mensagem."]
            lines.append(f"[{message.label}] message_id={message.message_id or 'n/a'}")
            lines.extend(details)
        if presentation.details:
            lines.append("[Conversa]")
            lines.extend(presentation.details)
        TextCard(self.details_scroll.body, "Detalhes", "\n".join(lines), "tecnico sanitizado", height=10).pack(fill="both", padx=8, pady=4)

    def _render_artifact_actions(self, presentation) -> None:
        for message in presentation.messages:
            actionable = [artifact for artifact in message.artifacts if artifact.actionable]
            if not actionable:
                continue
            card = ActionCard(self.details_scroll.body, "Artifacts", f"{message.label} gerou {len(actionable)} artifact(s) baixavel(is).", "download protegido por token")
            for artifact in actionable:
                NeonButton(
                    card.actions,
                    artifact.label,
                    command=lambda item=artifact: self._download_artifact(item),
                    accent=COLORS["green"],
                ).pack(side="left", padx=6)
            card.pack(fill="x", padx=8, pady=6)

    def _download_artifact(self, artifact: ArtifactPresentation) -> None:
        if not artifact.artifact_id:
            TextCard(self.details_scroll.body, "Artifact", "Artifact sem id acionavel. Nao e possivel baixar por este cliente.").pack(fill="x", padx=8, pady=4)
            return
        filename = safe_filename(artifact.filename)
        target_name = filedialog.asksaveasfilename(initialfile=filename, title="Salvar artifact")
        if not target_name:
            return
        result = self.artifact_client.download(artifact.artifact_id)
        ok = self.artifact_client.save_download(result, Path(target_name))
        message = f"Download concluido em {target_name}" if ok else f"Falha no download: {result.error or result.status_code}"
        TextCard(self.details_scroll.body, "Download", message, "token usado apenas no header", height=3).pack(fill="x", padx=8, pady=4)
