from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.manual_inference_result import ManualInferenceResult
from aipinho.schemas.models.real_inference_run import RealInferenceRun
from aipinho.utils.yaml_loader import load_yaml_file


class RealInferenceRunStore:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "real_inference_run_store.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        store = self.config.get("store", {}) if isinstance(self.config.get("store", {}), dict) else {}
        self.runs_dir = PATHS.project_root / str(store.get("runs_dir", "data/runtime/model_runs"))
        self.events_dir = PATHS.project_root / str(store.get("events_dir", "data/runtime/model_runs/events"))
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def save_run(self, result: ManualInferenceResult) -> RealInferenceRun:
        run = RealInferenceRun(
            run_id=result.run_id,
            profile_id=result.profile_id,
            provider_id=result.provider_id,
            model_id=result.model_id,
            status=result.status,
            real_inference=result.real_inference,
            process_started=result.process_started,
            output_preview=result.output_preview,
            warnings=result.warnings,
            violations=result.violations,
            audit_event_id=result.audit_event_id,
        )
        (self.runs_dir / f"{run.run_id}.json").write_text(json.dumps(run.model_dump(), ensure_ascii=True, sort_keys=True, indent=2), encoding="utf-8")
        return run

    def get_run(self, run_id: str) -> dict[str, object] | None:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def append_event(self, run_id: str, event: dict[str, object]) -> None:
        path = self.events_dir / f"{run_id}.jsonl"
        path.open("a", encoding="utf-8").write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")

    def list_events(self, run_id: str) -> list[dict[str, object]]:
        path = self.events_dir / f"{run_id}.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "real_inference_run_store", "runs_dir": str(self.runs_dir), "events_dir": str(self.events_dir)}
