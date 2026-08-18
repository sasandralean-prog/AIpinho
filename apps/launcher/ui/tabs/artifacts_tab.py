from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

from apps.launcher.ui.components.component_base import ActionCard, COLORS, NeonButton, ScrollableFrame, TextCard
from apps.launcher.ui.utils.safe_filename import safe_filename


class ArtifactsTab(ttk.Frame):
    def __init__(self, parent, artifact_client) -> None:
        super().__init__(parent)
        self.artifact_client = artifact_client
        bar = tk.Frame(self, background=COLORS["background"])
        bar.pack(fill="x", padx=8, pady=8)
        tk.Label(bar, text="Artifact ID", background=COLORS["background"], foreground=COLORS["cyan"]).pack(side="left")
        self.artifact_id = tk.Entry(
            bar,
            background=COLORS["terminal"],
            foreground=COLORS["green"],
            insertbackground=COLORS["cyan"],
            relief="flat",
            font=("Segoe UI", 12),
        )
        self.artifact_id.pack(side="left", fill="x", expand=True, padx=8, ipady=8)
        NeonButton(bar, "Metadata", command=self.show_metadata).pack(side="left", padx=4)
        NeonButton(bar, "Baixar", command=self.download_current, accent=COLORS["green"]).pack(side="left")
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        TextCard(
            self.scroll.body,
            "Artifacts",
            "Artifacts vindos do Chat aparecem como botoes na aba Chat. Aqui voce pode inspecionar ou baixar um artifact_id real.",
            "token no header; raw URL oculta",
            height=4,
        ).pack(fill="x", padx=8, pady=8)

    def show_metadata(self) -> None:
        artifact_id = self.artifact_id.get().strip()
        if not artifact_id:
            return
        result = self.artifact_client.metadata(artifact_id)
        TextCard(self.scroll.body, "Metadata", str(result.data if result.ok else result.error), f"artifact_id={artifact_id}", height=8).pack(fill="x", padx=8, pady=4)

    def download_current(self) -> None:
        artifact_id = self.artifact_id.get().strip()
        if not artifact_id:
            return
        metadata = self.artifact_client.metadata(artifact_id)
        filename = self._filename(metadata.data) if metadata.ok else f"{artifact_id}.bin"
        target_name = filedialog.asksaveasfilename(initialfile=safe_filename(filename), title="Salvar artifact")
        if not target_name:
            return
        result = self.artifact_client.download(artifact_id)
        ok = self.artifact_client.save_download(result, Path(target_name))
        summary = f"Download concluido em {target_name}" if ok else f"Falha no download: {result.error or result.status_code}"
        card = ActionCard(self.scroll.body, "Download", summary, f"artifact_id={artifact_id}")
        card.pack(fill="x", padx=8, pady=4)

    def _filename(self, data: object) -> str:
        if isinstance(data, dict):
            artifact = data.get("artifact") if isinstance(data.get("artifact"), dict) else data
            name = artifact.get("filename") or artifact.get("name") if isinstance(artifact, dict) else None
            if name:
                return str(name)
        return "artifact.bin"
