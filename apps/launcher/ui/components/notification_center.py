from __future__ import annotations
import tkinter as tk
from apps.launcher.ui.components.component_base import SimpleCyberPanel
class NotificationCenter:
    def __init__(self, text: str = "", state: str = "info") -> None:
        self.text=text; self.state=state
    def render_text(self) -> str:
        return f"{self.state}: {self.text}".strip()
    def build(self,parent: tk.Misc) -> tk.Frame:
        return SimpleCyberPanel(parent, self.text, self.state)
