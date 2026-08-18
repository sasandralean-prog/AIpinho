from __future__ import annotations

import tkinter as tk


def copy_to_clipboard(widget: tk.Misc, text: str) -> None:
    widget.clipboard_clear()
    widget.clipboard_append(text)
