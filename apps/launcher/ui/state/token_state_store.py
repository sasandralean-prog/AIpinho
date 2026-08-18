from __future__ import annotations

from apps.launcher.ui.state.ui_state_store import JsonStateStore


class TokenStateStore(JsonStateStore):
    filename = "token_state.json"

    def clear(self) -> dict[str, object]:
        return self.save({})
