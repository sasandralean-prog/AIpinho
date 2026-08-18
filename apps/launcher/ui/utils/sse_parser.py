from __future__ import annotations

from apps.launcher.ui.api.realtime_client import RealtimeClient


def parse_sse(text: str) -> list[dict[str, object]]:
    return RealtimeClient("http://127.0.0.1:9089").parse_sse(text)
