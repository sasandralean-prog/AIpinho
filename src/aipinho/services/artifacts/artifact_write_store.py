from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_write_event import ArtifactWriteEvent
from aipinho.schemas.artifacts.artifact_write_result import ArtifactWriteResult
from aipinho.schemas.artifacts.artifact_write_run import ArtifactWriteRun
from aipinho.services.artifacts.artifact_secret_scanner import ArtifactSecretScanner
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactWriteStore:
    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_write_store_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        configured = str((self.policy.get("store", {}) or {}).get("path", "data/runtime/artifact_writes"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)
        self.secret_scanner = ArtifactSecretScanner()

    def create_run(self, run: ArtifactWriteRun) -> ArtifactWriteRun:
        self._write(self._run_path(run.write_run_id), run.model_dump())
        return run

    def update_run(self, run: ArtifactWriteRun) -> ArtifactWriteRun:
        return self.create_run(run)

    def get_run(self, write_run_id: str) -> ArtifactWriteRun | None:
        data = self._read(self._run_path(write_run_id))
        return ArtifactWriteRun.model_validate(data) if data else None

    def list_runs(self, *, status: str | None = None, preview_id: str | None = None, approval_id: str | None = None, limit: int = 100) -> list[ArtifactWriteRun]:
        runs: list[ArtifactWriteRun] = []
        root = self.root / "runs"
        if not root.exists():
            return []
        for path in root.glob("artifact_write_run_*.json"):
            try:
                run = ArtifactWriteRun.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))
            except Exception:
                continue
            if status and run.status != status:
                continue
            if preview_id and run.preview_id != preview_id:
                continue
            if approval_id and run.approval_id != approval_id:
                continue
            runs.append(run)
        return sorted(runs, key=lambda item: item.created_at, reverse=True)[: max(1, min(limit, 1000))]

    def append_event(self, event: ArtifactWriteEvent) -> None:
        events = self.get_events(event.write_run_id)
        events.append(event)
        self._write(self._events_path(event.write_run_id), [item.model_dump() for item in events])

    def get_events(self, write_run_id: str) -> list[ArtifactWriteEvent]:
        data = self._read(self._events_path(write_run_id)) or []
        return [ArtifactWriteEvent.model_validate(item) for item in data if isinstance(item, dict)]

    def save_result(self, result: ArtifactWriteResult) -> ArtifactWriteResult:
        self._write(self._result_path(result.write_run_id), result.model_dump())
        return result

    def get_result(self, write_run_id: str) -> ArtifactWriteResult | None:
        data = self._read(self._result_path(write_run_id))
        return ArtifactWriteResult.model_validate(data) if data else None

    def save_trace(self, write_run_id: str, trace: list[str]) -> None:
        self._write(self._trace_path(write_run_id), trace)

    def get_trace(self, write_run_id: str) -> list[str]:
        data = self._read(self._trace_path(write_run_id)) or []
        return [str(item) for item in data]

    def sanitize(self, value: Any, *, key: str = "") -> Any:
        if key.lower() in {"content", "raw", "secret", "token", "api_key", "password"}:
            return "[omitted_by_artifact_write_store]"
        if isinstance(value, dict):
            return {str(k): self.sanitize(v, key=str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            return self.secret_scanner.redact(value)
        return value

    def _run_path(self, write_run_id: str) -> Path:
        self._validate_id(write_run_id)
        return resolve_within_root(self.root / "runs" / f"{write_run_id}.json", self.root)

    def _events_path(self, write_run_id: str) -> Path:
        self._validate_id(write_run_id)
        return resolve_within_root(self.root / "events" / f"{write_run_id}.events.json", self.root)

    def _result_path(self, write_run_id: str) -> Path:
        self._validate_id(write_run_id)
        return resolve_within_root(self.root / "results" / f"{write_run_id}.result.json", self.root)

    def _trace_path(self, write_run_id: str) -> Path:
        self._validate_id(write_run_id)
        return resolve_within_root(self.root / "traces" / f"{write_run_id}.trace.json", self.root)

    def _validate_id(self, write_run_id: str) -> None:
        if not re.fullmatch(r"artifact_write_run_[a-f0-9]+", write_run_id):
            raise ValueError("invalid_artifact_write_run_id")

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
        return {"status": "ok", "service": "artifact_write_store", "path": str(self.root), "stores_full_content": False}
