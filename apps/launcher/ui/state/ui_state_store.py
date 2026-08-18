from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
STATE_ROOT = PROJECT_ROOT / "data" / "runtime" / "launcher" / "state"


class JsonStateStore:
    filename = "ui_state.json"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or STATE_ROOT / self.filename

    def load(self) -> dict[str, Any]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
        return data

    def set(self, key: str, value: Any) -> dict[str, Any]:
        data = self.load()
        data[key] = value
        return self.save(data)

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)
