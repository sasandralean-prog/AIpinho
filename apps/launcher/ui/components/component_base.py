from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from apps.launcher.ui.utils.formatting import as_text
from apps.launcher.ui.utils.redaction import redact

COLORS = {
    "background": "#020406",
    "terminal": "#03070A",
    "card": "#0B0F14",
    "card_deep": "#071018",
    "cyan": "#00E5FF",
    "cyan_muted": "#7DEBFF",
    "green": "#39FF14",
    "pink": "#FF2BD6",
    "danger": "#FF1493",
    "muted": "#60707A",
    "white": "#E8F7FF",
}

FONT_TEXT = ("Segoe UI", 13)
FONT_META = ("Consolas", 10)
FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_TERMINAL = ("Consolas", 13)


def _rounded_rectangle(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedSurface(tk.Frame):
    def __init__(self, parent: tk.Misc, border: str = COLORS["cyan"], fill: str = COLORS["card"], radius: int = 18) -> None:
        super().__init__(parent, background=COLORS["background"])
        self.border = border
        self.fill = fill
        self.radius = radius
        self.canvas = tk.Canvas(self, highlightthickness=0, background=COLORS["background"])
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, background=fill)
        self._window_id = self.canvas.create_window((14, 14), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._redraw)
        self.inner.bind("<Configure>", self._resize_to_content)

    def _redraw(self, event=None) -> None:
        width = max(self.canvas.winfo_width(), 260)
        height = max(self.canvas.winfo_height(), self.inner.winfo_reqheight() + 28)
        self.canvas.delete("surface")
        _rounded_rectangle(
            self.canvas,
            2,
            2,
            width - 2,
            height - 2,
            self.radius,
            fill=self.fill,
            outline=self.border,
            width=2,
            tags="surface",
        )
        self.canvas.tag_lower("surface")
        self.canvas.itemconfigure(self._window_id, width=max(100, width - 28))

    def _resize_to_content(self, _event=None) -> None:
        height = max(72, self.inner.winfo_reqheight() + 28)
        self.canvas.configure(height=height)
        self._redraw()


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, background="#050608")
        self.body = tk.Frame(self.canvas, background=COLORS["background"])
        self.body.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._window_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self._resize_body)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.pack(side="left", fill="both", expand=True)

    def _resize_body(self, event) -> None:
        self.canvas.itemconfigure(self._window_id, width=event.width)

    def _bind_mousewheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event) -> str | None:
        pointer_x = self.winfo_pointerx()
        pointer_y = self.winfo_pointery()
        left = self.winfo_rootx()
        top = self.winfo_rooty()
        right = left + self.winfo_width()
        bottom = top + self.winfo_height()
        if not (left <= pointer_x <= right and top <= pointer_y <= bottom):
            return None
        if getattr(event, "num", None) == 4:
            delta = -3
        elif getattr(event, "num", None) == 5:
            delta = 3
        else:
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta:
            self.canvas.yview_scroll(delta, "units")
        return "break"


class PlaceholderEntry(tk.Entry):
    def __init__(
        self,
        parent: tk.Misc,
        placeholder: str,
        *,
        font=("Segoe UI", 12),
        background: str = COLORS["background"],
    ) -> None:
        super().__init__(
            parent,
            background=background,
            foreground=COLORS["green"],
            insertbackground=COLORS["cyan"],
            relief="flat",
            font=font,
        )
        self.placeholder = placeholder
        self._showing_placeholder = False
        self.bind("<FocusIn>", self._hide_placeholder)
        self.bind("<FocusOut>", self._show_placeholder_if_empty)
        self.clear()

    def get_value(self) -> str:
        return "" if self._showing_placeholder else self.get().strip()

    def clear(self) -> None:
        self.delete(0, "end")
        self._show_placeholder_if_empty()

    def _hide_placeholder(self, _event=None) -> None:
        if not self._showing_placeholder:
            return
        self.delete(0, "end")
        self.configure(foreground=COLORS["green"])
        self._showing_placeholder = False

    def _show_placeholder_if_empty(self, _event=None) -> None:
        if self.get():
            return
        self._showing_placeholder = True
        self.configure(foreground=COLORS["muted"])
        self.insert(0, self.placeholder)


class TextCard(tk.Frame):
    def __init__(self, parent: tk.Misc, title: str, text: str = "", meta: str = "", height: int = 5) -> None:
        tk.Frame.__init__(self, parent, background=COLORS["background"])
        self.surface = RoundedSurface(self, border=COLORS["cyan"], fill=COLORS["card"])
        self.surface.pack(fill="both", expand=True)
        tk.Label(self.surface.inner, text=title, background=COLORS["card"], foreground=COLORS["cyan"], font=FONT_TITLE).pack(anchor="w", padx=10, pady=(8, 2))
        self.meta = tk.Label(self.surface.inner, text=meta, background=COLORS["card"], foreground=COLORS["cyan_muted"], font=FONT_META)
        if meta:
            self.meta.pack(anchor="w", padx=8, pady=(4, 0))
        terminal = tk.Frame(self.surface.inner, background=COLORS["terminal"])
        terminal.pack(fill="both", expand=True, padx=10, pady=10)
        self.text = tk.Text(
            terminal,
            height=height,
            wrap="word",
            background=COLORS["terminal"],
            foreground=COLORS["green"],
            insertbackground=COLORS["cyan"],
            selectbackground="#16394A",
            selectforeground=COLORS["white"],
            relief="flat",
            padx=8,
            pady=8,
            font=FONT_TERMINAL,
        )
        self.text.bind("<MouseWheel>", self._scroll_text)
        self.text.bind("<Button-4>", self._scroll_text)
        self.text.bind("<Button-5>", self._scroll_text)
        self.text.pack(side="left", fill="both", expand=True)
        self.set_text(text)

    def set_text(self, text: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", redact(text))
        self.text.configure(state="disabled")

    def _scroll_text(self, event) -> str:
        if getattr(event, "num", None) == 4:
            delta = -3
        elif getattr(event, "num", None) == 5:
            delta = 3
        else:
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta:
            self.text.yview_scroll(delta, "units")
        return "break"


class Badge(ttk.Label):
    def __init__(self, parent: tk.Misc, text: str) -> None:
        super().__init__(parent, text=text)


class CopyButton(tk.Canvas):
    def __init__(self, parent: tk.Misc, text_provider) -> None:
        super().__init__(parent, height=36, width=120, highlightthickness=0, background=COLORS["card"])
        self.text_provider = text_provider
        self.bind("<Button-1>", lambda _event: self._copy(parent, self.text_provider()))
        self.bind("<Enter>", lambda _event: self._draw(True))
        self.bind("<Leave>", lambda _event: self._draw(False))
        self._draw(False)

    def _draw(self, hover: bool) -> None:
        self.delete("all")
        fill = "#102630" if hover else COLORS["card_deep"]
        _rounded_rectangle(self, 2, 2, 118, 34, 16, fill=fill, outline=COLORS["cyan"], width=2)
        self.create_text(60, 18, text="Copiar", fill=COLORS["cyan"], font=("Segoe UI", 10, "bold"))

    def _copy(self, widget: tk.Misc, text: str) -> None:
        widget.clipboard_clear()
        widget.clipboard_append(text)


class CyberChip(tk.Canvas):
    def __init__(self, parent: tk.Misc, text: str, command=None, selected: bool = False, width: int | None = None) -> None:
        super().__init__(
            parent,
            height=42,
            width=width or max(120, len(text) * 10 + 36),
            highlightthickness=0,
            background=COLORS["background"],
        )
        self.text = text
        self.command = command
        self.selected = selected
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda _event: self._draw(hover=True))
        self.bind("<Leave>", lambda _event: self._draw(hover=False))
        self._draw()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._draw()

    def _draw(self, hover: bool = False) -> None:
        self.delete("all")
        accent = COLORS["green"] if self.selected else COLORS["cyan"]
        fill = "#102914" if self.selected else ("#102630" if hover else COLORS["terminal"])
        _rounded_rectangle(self, 2, 3, int(self["width"]) - 2, 39, 16, fill=fill, outline=accent, width=2)
        self.create_text(int(self["width"]) // 2, 21, text=self.text, fill=accent, font=("Segoe UI", 11, "bold"))

    def _click(self, _event=None) -> None:
        if self.command:
            self.command()


class SimpleCyberPanel(tk.Frame):
    def __init__(self, parent: tk.Misc, text: str, state: str = "info", wraplength: int = 820) -> None:
        super().__init__(parent, background=COLORS["background"])
        lower = f"{state} {text}".lower()
        accent = COLORS["pink"] if any(word in lower for word in ("erro", "error", "falha", "danger", "perigo", "blocked", "bloqueado", "atencao")) else COLORS["cyan"]
        surface = RoundedSurface(self, border=accent, fill=COLORS["card"])
        surface.pack(fill="both", expand=True)
        tk.Label(
            surface.inner,
            text=f"{state}: {text}".strip(),
            wraplength=wraplength,
            justify="left",
            background=COLORS["card"],
            foreground=COLORS["green"],
            font=FONT_TEXT,
        ).pack(anchor="w", padx=10, pady=10)


class RawCollapsible(tk.Frame):
    def __init__(self, parent: tk.Misc, raw_provider) -> None:
        super().__init__(parent, background=COLORS["background"])
        self.raw_provider = raw_provider
        self.visible = False
        self.surface = RoundedSurface(self, border=COLORS["pink"], fill=COLORS["card"])
        self.surface.pack(fill="both", expand=True)
        tk.Label(self.surface.inner, text="Raw sanitizado", background=COLORS["card"], foreground=COLORS["pink"], font=FONT_TITLE).pack(anchor="w", padx=10, pady=(8, 3))
        self.button = tk.Canvas(self.surface.inner, height=36, width=140, highlightthickness=0, background=COLORS["card"])
        self.button.bind("<Button-1>", lambda _event: self.toggle())
        self.button.bind("<Enter>", lambda _event: self._draw_raw_button(True))
        self.button.bind("<Leave>", lambda _event: self._draw_raw_button(False))
        self.button.pack(anchor="w", padx=10, pady=4)
        self._raw_button_label = "Mostrar raw"
        self._draw_raw_button(False)
        self.text = tk.Text(
            self.surface.inner,
            height=8,
            wrap="word",
            background=COLORS["terminal"],
            foreground=COLORS["cyan_muted"],
            selectbackground="#16394A",
            selectforeground=COLORS["white"],
            relief="flat",
            font=FONT_TERMINAL,
        )
        self.text.bind("<MouseWheel>", self._scroll_text)
        self.text.bind("<Button-4>", self._scroll_text)
        self.text.bind("<Button-5>", self._scroll_text)

    def toggle(self) -> None:
        self.visible = not self.visible
        if self.visible:
            self.text.pack(fill="both", expand=True, padx=8, pady=8)
            self.text.delete("1.0", "end")
            self.text.insert("1.0", redact(as_text(self.raw_provider())))
            self._raw_button_label = "Ocultar raw"
            self._draw_raw_button(False)
        else:
            self.text.pack_forget()
            self._raw_button_label = "Mostrar raw"
            self._draw_raw_button(False)

    def _draw_raw_button(self, hover: bool) -> None:
        self.button.delete("all")
        fill = "#251028" if hover else COLORS["card_deep"]
        _rounded_rectangle(self.button, 2, 2, 138, 34, 16, fill=fill, outline=COLORS["pink"], width=2)
        self.button.create_text(70, 18, text=self._raw_button_label, fill=COLORS["pink"], font=("Segoe UI", 10, "bold"))

    def _scroll_text(self, event) -> str:
        if getattr(event, "num", None) == 4:
            delta = -3
        elif getattr(event, "num", None) == 5:
            delta = 3
        else:
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta:
            self.text.yview_scroll(delta, "units")
        return "break"


class EventCard(TextCard):
    @classmethod
    def from_event(cls, parent: tk.Misc, event: dict[str, Any]) -> "EventCard":
        title = f"{event.get('event_type', 'unknown')} [{event.get('severity', 'info')}]"
        meta = f"source={event.get('source_service', 'unknown')} status={event.get('status', 'unknown')} visibility={event.get('visibility', 'unknown')}"
        return cls(parent, title, as_text(event.get("human_summary", "")), meta)


class ActionCard(tk.Frame):
    def __init__(self, parent: tk.Misc, title: str, summary: str = "", meta: str = "") -> None:
        tk.Frame.__init__(self, parent, background=COLORS["background"])
        border = COLORS["pink"] if any(word in f"{title} {summary} {meta}".lower() for word in ("erro", "perigo", "atencao", "blocked", "falha")) else COLORS["cyan"]
        self.surface = RoundedSurface(self, border=border, fill=COLORS["card"])
        self.surface.pack(fill="both", expand=True)
        tk.Label(self.surface.inner, text=title, background=COLORS["card"], foreground=border, font=FONT_TITLE).pack(anchor="w", padx=10, pady=(8, 3))
        if summary:
            tk.Label(self.surface.inner, text=summary, wraplength=920, background=COLORS["card"], foreground=COLORS["green"], justify="left", font=FONT_TEXT).pack(anchor="w", padx=10, pady=(2, 3))
        if meta:
            tk.Label(self.surface.inner, text=meta, wraplength=920, background=COLORS["card"], foreground=COLORS["cyan_muted"], justify="left", font=FONT_META).pack(anchor="w", padx=10, pady=(0, 6))
        self.actions = tk.Frame(self.surface.inner, background=COLORS["card"])
        self.actions.pack(fill="x", padx=10, pady=(4, 10))


class NeonButton(tk.Canvas):
    def __init__(self, parent: tk.Misc, text: str, command=None, accent: str = COLORS["cyan"]) -> None:
        super().__init__(parent, height=38, width=max(120, len(text) * 9 + 34), highlightthickness=0, background=COLORS["card"])
        self.text = text
        self.command = command
        self.accent = accent
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda _event: self._draw(hover=True))
        self.bind("<Leave>", lambda _event: self._draw(hover=False))
        self._draw()

    def _draw(self, hover: bool = False) -> None:
        self.delete("all")
        fill = "#102630" if hover else COLORS["card_deep"]
        _rounded_rectangle(self, 2, 2, int(self["width"]) - 2, 36, 16, fill=fill, outline=self.accent, width=2)
        self.create_text(int(self["width"]) // 2, 19, text=self.text, fill=self.accent, font=("Segoe UI", 10, "bold"))

    def _click(self, _event=None) -> None:
        if self.command:
            self.command()
