from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.evals.contracts import EvalRun


class EvalRunStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "evals"

    def save(self, run: EvalRun) -> EvalRun:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{run.result.eval_run_id}.json").write_text(json.dumps(run.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return run

    def get(self, eval_run_id: str) -> dict | None:
        path = self.root / f"{eval_run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict]:
        if not self.root.exists():
            return []
        out = []
        for path in sorted(self.root.glob("eval_run_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out
