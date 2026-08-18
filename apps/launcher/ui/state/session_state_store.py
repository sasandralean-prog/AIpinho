from __future__ import annotations

from apps.launcher.ui.state.ui_state_store import JsonStateStore


class SessionStateStore(JsonStateStore):
    filename = "session_state.json"

    def clear(self) -> dict[str, object]:
        return self.save({})
