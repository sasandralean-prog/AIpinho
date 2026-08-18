from __future__ import annotations

from apps.launcher.ui.utils.event_formatting import is_unknown_event


def visible_event(event: dict[str, object], known_contracts: set[str]) -> bool:
    if is_unknown_event(event, known_contracts):
        return False
    return str(event.get("visibility", "public")) not in {"hidden", "internal"}
