from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.retrieval_request import RetrievalResult
from aipinho.utils.safe_paths import resolve_within_root


class RetrievalAuditService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "retrieval"
        self.root.mkdir(parents=True, exist_ok=True)

    def save_result(self, result: RetrievalResult) -> RetrievalResult:
        path = resolve_within_root(self.root / f"{result.retrieval_id}.json", self.root)
        path.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def get_result(self, retrieval_id: str) -> dict[str, Any] | None:
        path = resolve_within_root(self.root / f"{retrieval_id}.json", self.root)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_results(self, limit: int = 100) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("retrieval_*.json"), reverse=True):
            items.append(json.loads(path.read_text(encoding="utf-8")))
            if len(items) >= limit:
                break
        return items

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_audit", "store_path": str(self.root), "raw_content_stored": False}
