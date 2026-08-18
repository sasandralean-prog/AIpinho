from __future__ import annotations

import tkinter as tk


def add_tab(container: tk.Misc, frame: tk.Frame, title: str) -> None:
    frame.place(in_=container, relx=0, rely=0, relwidth=1, relheight=1)
