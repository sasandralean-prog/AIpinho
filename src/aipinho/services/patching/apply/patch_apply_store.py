from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.apply.patch_apply_event import PatchApplyEvent
from aipinho.schemas.patching.apply.patch_apply_result import PatchApplyResult
from aipinho.schemas.patching.apply.patch_apply_run import PatchApplyRun
from aipinho.schemas.patching.apply.patch_apply_trace import PatchApplyTrace
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class PatchApplyStore:
    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "apply" / "patch_apply_store_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "apply")
        configured = str((self.policy.get("store", {}) or {}).get("path", "data/runtime/patch_apply_runs"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)
        self.secret_guard = SecretGuardService()

    def save_run(self, run: PatchApplyRun) -> PatchApplyRun:
        self._write(self._run_path(run.apply_run_id), run.model_dump())
        return run

    def get_run(self, apply_run_id: str) -> PatchApplyRun | None:
        data = self._read(self._run_path(apply_run_id))
        return PatchApplyRun.model_validate(data) if data else None

    def list_runs(self, *, plan_id: str | None = None, approval_id: str | None = None, status: str | None = None, limit: int = 100) -> list[PatchApplyRun]:
        runs: list[PatchApplyRun] = []
        root = self.root / "runs"
        if not root.exists():
            return []
        for path in root.glob("patch_apply_run_*.json"):
            try:
                run = PatchApplyRun.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))
            except Exception:
                continue
            if plan_id and run.plan_id != plan_id:
                continue
            if approval_id and run.approval_id != approval_id:
                continue
            if status and run.status != status:
                continue
            runs.append(run)
        return sorted(runs, key=lambda item: item.created_at, reverse=True)[: max(1, min(limit, 1000))]

    def append_event(self, event: PatchApplyEvent) -> PatchApplyEvent:
        events = self.get_events(event.apply_run_id)
        events.append(event)
        self._write(self._events_path(event.apply_run_id), [item.model_dump() for item in events])
        return event

    def get_events(self, apply_run_id: str) -> list[PatchApplyEvent]:
        data = self._read(self._events_path(apply_run_id)) or []
        return [PatchApplyEvent.model_validate(item) for item in data if isinstance(item, dict)]

    def save_result(self, result: PatchApplyResult) -> PatchApplyResult:
        self._write(self._result_path(result.apply_run_id), result.model_dump())
        return result

    def get_result(self, apply_run_id: str) -> PatchApplyResult | None:
        data = self._read(self._result_path(apply_run_id))
        return PatchApplyResult.model_validate(data) if data else None

    def save_trace(self, trace: PatchApplyTrace) -> PatchApplyTrace:
        self._write(self._trace_path(trace.apply_run_id), trace.model_dump())
        return trace

    def get_trace(self, apply_run_id: str) -> PatchApplyTrace | None:
        data = self._read(self._trace_path(apply_run_id))
        return PatchApplyTrace.model_validate(data) if data else None

    def sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): self.sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            return self.secret_guard.redact(value)[0]
        return value

    def _run_path(self, apply_run_id: str) -> Path:
        self._validate_id(apply_run_id)
        return resolve_within_root(self.root / "runs" / f"{apply_run_id}.json", self.root)

    def _events_path(self, apply_run_id: str) -> Path:
        self._validate_id(apply_run_id)
        return resolve_within_root(self.root / "events" / f"{apply_run_id}.events.json", self.root)

    def _result_path(self, apply_run_id: str) -> Path:
        self._validate_id(apply_run_id)
        return resolve_within_root(self.root / "results" / f"{apply_run_id}.result.json", self.root)

    def _trace_path(self, apply_run_id: str) -> Path:
        self._validate_id(apply_run_id)
        return resolve_within_root(self.root / "trace" / f"{apply_run_id}.trace.json", self.root)

    def _validate_id(self, apply_run_id: str) -> None:
        if not re.fullmatch(r"patch_apply_run_[a-f0-9]+", apply_run_id):
            raise ValueError("invalid_patch_apply_run_id")

    def _write(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.sanitize(value), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def _read(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def status(self) -> dict[str, object]:
        self.root.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "service": "patch_apply_store", "path": str(self.root)}
