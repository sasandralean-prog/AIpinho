from __future__ import annotations

from pathlib import Path
from tkinter import ttk
from typing import Any

import yaml


def _theme_config() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "config" / "launcher" / "desktop_ui_theme.yaml"
    if not path.exists():
        path = Path(__file__).resolve().parents[4] / "config" / "launcher" / "desktop_ui_theme.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        data = {}
    return data.get("theme", {}) if isinstance(data, dict) else {}


def apply_theme(root) -> None:
    colors = {
        "background": "#050608",
        "foreground": "#39ff14",
        "metainfo": "#00e5ff",
        "danger": "#ff2ea6",
        "muted": "#6d7a88",
        "card_background": "#0b0f14",
        **_theme_config(),
    }
    root.configure(background=colors["background"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TFrame", background=colors["background"])
    style.configure("TLabel", background=colors["background"], foreground=colors["foreground"], font=("Segoe UI", 12))
    style.configure("Meta.TLabel", background=colors["background"], foreground=colors["metainfo"], font=("Consolas", 10))
    style.configure("TButton", padding=(12, 8), background=colors["card_background"], foreground=colors["metainfo"], font=("Segoe UI", 10, "bold"))
    style.map("TButton", foreground=[("active", colors["foreground"])], background=[("active", "#102630")])
    style.configure("TEntry", fieldbackground="#03070A", background="#03070A", foreground=colors["foreground"], insertcolor=colors["metainfo"], padding=(8, 6))
    style.configure("TCombobox", fieldbackground="#03070A", background=colors["card_background"], foreground=colors["foreground"], arrowcolor=colors["metainfo"], padding=(8, 6))
    style.configure("TLabelframe", background=colors["background"], foreground=colors["metainfo"])
    style.configure("TLabelframe.Label", background=colors["background"], foreground=colors["metainfo"], font=("Segoe UI", 10, "bold"))
    style.configure("Neon.TLabelframe", background=colors["card_background"], bordercolor=colors["metainfo"], lightcolor=colors["metainfo"], darkcolor=colors["card_background"])
