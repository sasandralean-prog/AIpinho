from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DesktopAgentState:
    selected_session_by_agent: dict[str, str] = field(default_factory=dict)
    latest_event_by_session: dict[str, str] = field(default_factory=dict)
    active_run_by_session: dict[str, str] = field(default_factory=dict)
    display_mode_by_agent: dict[str, str] = field(default_factory=dict)
