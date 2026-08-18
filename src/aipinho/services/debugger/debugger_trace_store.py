from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS


class DebuggerTraceStore:
    def __init__(self, store_dir: Path | None = None) -> None:
        self.store_dir = store_dir or PATHS.project_root / "data" / "runtime" / "model_traces"

    def get(self, trace_id: str) -> dict[str, Any] | None:
        path = self.store_dir / f"{trace_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.store_dir.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(self.store_dir.glob("trace_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                items.append(loaded)
            except Exception:
                continue
        return items

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "debugger_trace_store", "read_only": True, "trace_count": len(self.list_recent())}
