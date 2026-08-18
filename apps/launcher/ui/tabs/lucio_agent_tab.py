from __future__ import annotations

from apps.launcher.ui.agent_catalog import agent_endpoint
from apps.launcher.ui.api.agent_api_client import DesktopAgentApiClient
from apps.launcher.ui.tabs.agent_desktop_tab import AgentDesktopTab


class LucioAgentTab(AgentDesktopTab):
    def __init__(self, parent, base_url: str, launcher_state) -> None:
        client = DesktopAgentApiClient(
            base_url,
            agent_endpoint("lucio"),
            token=launcher_state.token,
        )
        super().__init__(parent, client, launcher_state)
