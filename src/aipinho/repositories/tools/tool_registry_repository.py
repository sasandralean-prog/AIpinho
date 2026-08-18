from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS


class ToolRegistryRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "tools"

    def save_registry(self, entries: list[dict[str, Any]]) -> None:
        path = self.root / "registry" / "registry.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, indent=2, ensure_ascii=True), encoding="utf-8")

    def save_invocation_preview(self, payload: dict[str, Any]) -> None:
        preview_id = str(payload["invocation_preview_id"])
        path = self.root / "invocation_previews" / f"{preview_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
