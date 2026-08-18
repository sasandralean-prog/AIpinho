from __future__ import annotations

import tkinter as tk
from pathlib import Path
import ctypes
import sys

from apps.launcher.ui.api.agent_console_client import AgentConsoleClient
from apps.launcher.ui.api.agent_marketplace_client import AgentMarketplaceClient
from apps.launcher.ui.api.artifact_client import ArtifactClient
from apps.launcher.ui.api.chat_client import ChatClient
from apps.launcher.ui.api.connection_client import ConnectionClient
from apps.launcher.ui.api.dashboard_client import DashboardClient
from apps.launcher.ui.api.debugger_client import DebuggerClient
from apps.launcher.ui.api.event_client import EventClient
from apps.launcher.ui.api.event_contract_client import EventContractClient
from apps.launcher.ui.api.governance_client import GovernanceClient
from apps.launcher.ui.api.ux_client import UXClient
from apps.launcher.ui.api.monitor_client import MonitorClient
from apps.launcher.ui.api.raw_client import RawClient
from apps.launcher.ui.api.pipeline_client import PipelineClient
from apps.launcher.ui.api.transfer_client import TransferClient
from apps.launcher.ui.api.universal_approver_client import UniversalApproverClient
from apps.launcher.ui.launcher_state import LauncherState
from apps.launcher.ui.launcher_theme import apply_theme
from apps.launcher.ui.components.component_base import COLORS, CyberChip
from apps.launcher.ui.tabs.agent_console_tab import AgentConsoleTab
from apps.launcher.ui.tabs.agent_marketplace_tab import AgentMarketplaceTab
from apps.launcher.ui.tabs.chat_tab import ChatTab
from apps.launcher.ui.tabs.codex_agent_tab import CodexAgentTab
from apps.launcher.ui.tabs.artifacts_tab import ArtifactsTab
from apps.launcher.ui.tabs.dashboard_tab import DashboardTab
from apps.launcher.ui.tabs.debugger_tab import DebuggerTab
from apps.launcher.ui.tabs.gemini_executor_tab import GeminiExecutorTab
from apps.launcher.ui.tabs.pipeline_tab import PipelineTab
from apps.launcher.ui.tabs.planning_tab import PlanningTab
from apps.launcher.ui.tabs.settings_tab import SettingsTab
from apps.launcher.ui.tabs.universal_approvers_tab import UniversalApproversTab


class LauncherApp:
    def __init__(self, state: LauncherState | None = None) -> None:
        self.state = state or LauncherState.load()
        self.root = tk.Tk()
        self.root.title("AIpinho Launcher")
        self.root.geometry("1280x820")
        self._apply_icon()
        apply_theme(self.root)
        self._apply_window_chrome()
        self.clients = self._clients()
        self.chrome_frame = tk.Frame(self.root, background=COLORS["background"], highlightthickness=2, highlightbackground=COLORS["cyan"])
        self.chrome_frame.pack(fill="both", expand=True)
        self.tab_bar = tk.Frame(self.chrome_frame, background=COLORS["background"])
        self.tab_bar.pack(fill="x", padx=10, pady=(10, 6))
        self.content = tk.Frame(self.chrome_frame, background=COLORS["background"])
        self.content.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tabs: dict[str, tk.Frame] = {}
        self.tab_chips: dict[str, CyberChip] = {}
        self._build_tabs()
        self._select_tab("⌂ Dashboard")

    def _clients(self) -> dict[str, object]:
        token = self.state.token
        return {
            "monitor": MonitorClient(self.state.monitor_url, token=token),
            "connection": ConnectionClient(self.state.monitor_url, token=token),
            "dashboard": DashboardClient(self.state.core_url, token=token),
            "events": EventClient(self.state.core_url, token=token),
            "contracts": EventContractClient(self.state.core_url, token=token),
            "chat": ChatClient(self.state.core_url, token=token),
            "artifacts": ArtifactClient(self.state.artifact_url, token=token),
            "pipeline": PipelineClient(self.state.core_url, token=token),
            "debugger": DebuggerClient(self.state.core_url, token=token),
            "ux": UXClient(self.state.core_url, token=token),
            "raw": RawClient(self.state.core_url, token=token),
            "transfers": TransferClient(self.state.core_url, token=token),
            "agent_console": AgentConsoleClient(self.state.core_url, token=token),
            "agent_marketplace": AgentMarketplaceClient(self.state.core_url, token=token),
            "governance": GovernanceClient(self.state.core_url, token=token),
            "universal_approvers": UniversalApproverClient(self.state.core_url, token=token),
        }

    def _build_tabs(self) -> None:
        self._add_tab("⌂ Dashboard", DashboardTab(self.content, self.clients["dashboard"], self.clients["monitor"], self.clients["events"], self.clients["contracts"]))
        self._add_tab("Agentes", AgentConsoleTab(self.content, self.clients["agent_console"]))
        self._add_tab("Agent Marketplace", AgentMarketplaceTab(self.content, self.clients["agent_marketplace"]))
        self._add_tab(
            "✧ Chat",
            ChatTab(
                self.content,
                self.clients["chat"],
                self.clients["artifacts"],
                self.state,
            ),
        )
        self._add_tab("✦ Gemini", GeminiExecutorTab(self.content, self.state.core_url, self.state))
        self._add_tab("⌬ Codex", CodexAgentTab(self.content, self.state.core_url, self.state))
        self._add_tab("Planning", PlanningTab(self.content, self.clients["pipeline"]))
        self._add_tab("➢ Pipeline", PipelineTab(self.content, self.clients["pipeline"]))
        self._add_tab("✓ Approvers", UniversalApproversTab(self.content, self.clients["universal_approvers"]))
        self._add_tab("✾ Debugger 2.0", DebuggerTab(self.content, self.clients["debugger"], self.clients["events"], self.clients["contracts"]))
        self._add_tab("⚙ Config", SettingsTab(self.content, self.clients["connection"], self.clients["contracts"], self.clients["monitor"], self.state, self.clients["governance"]))

    def _add_tab(self, title: str, frame: tk.Frame) -> None:
        self.tabs[title] = frame
        frame.configure(style="TFrame")
        frame.place(in_=self.content, relx=0, rely=0, relwidth=1, relheight=1)
        chip = CyberChip(self.tab_bar, title, command=lambda value=title: self._select_tab(value), selected=False)
        chip.pack(side="left", padx=(0, 8), pady=2)
        self.tab_chips[title] = chip

    def _select_tab(self, title: str) -> None:
        for tab_title, frame in self.tabs.items():
            if tab_title == title:
                frame.lift()
                activate = getattr(frame, "activate", None)
                if callable(activate):
                    activate()
            else:
                deactivate = getattr(frame, "deactivate", None)
                if callable(deactivate):
                    deactivate()
            self.tab_chips[tab_title].set_selected(tab_title == title)

    def run(self) -> None:
        self.root.mainloop()

    def _apply_icon(self) -> None:
        icon = Path(__file__).resolve().parents[1] / "assets" / "aipinho_launcher.ico"
        if icon.exists():
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass

    def _apply_window_chrome(self) -> None:
        if sys.platform != "win32":
            return
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            dark = ctypes.c_int(1)
            for attribute in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(dark), ctypes.sizeof(dark))
            caption_color = ctypes.c_int(0x060402)
            border_color = ctypes.c_int(0xFFE500)
            text_color = ctypes.c_int(0xFFE500)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), ctypes.sizeof(border_color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))
        except Exception:
            pass
