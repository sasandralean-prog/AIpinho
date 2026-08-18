from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_model_binding import RoleInferenceResult, RoleModelRun


class RoleModelRunStore:
    def __init__(self, store_dir: Path | None = None) -> None:
        self.store_dir = store_dir or PATHS.project_root / "data" / "runtime" / "role_model_runs"

    def save(self, run: RoleModelRun) -> RoleModelRun:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        (self.store_dir / f"{run.result.run_id}.json").write_text(json.dumps(run.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return run

    def get(self, run_id: str) -> RoleModelRun | None:
        path = self.store_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return RoleModelRun(**json.loads(path.read_text(encoding="utf-8")))

    def list_runs(self, *, role_id: str | None = None, status: str | None = None, model_id: str | None = None) -> list[RoleInferenceResult]:
        if not self.store_dir.exists():
            return []
        runs: list[RoleInferenceResult] = []
        for path in sorted(self.store_dir.glob("role_model_run_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                run = RoleModelRun(**json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            result = run.result
            if role_id and result.role_id != role_id:
                continue
            if status and result.status != status:
                continue
            if model_id and result.selected_model_id != model_id:
                continue
            runs.append(result)
        return runs

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_model_run_store", "runs": len(self.list_runs())}
