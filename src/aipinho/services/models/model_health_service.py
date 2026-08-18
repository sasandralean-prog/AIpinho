from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_health_status import ModelHealthStatus
from aipinho.services.models.model_registry_service import ModelRegistryService


class ModelHealthService:
    def __init__(self, store_dir: Path | None = None, registry: ModelRegistryService | None = None) -> None:
        self.store_dir = store_dir or PATHS.project_root / "data" / "runtime" / "model_doctor"
        self.registry = registry or ModelRegistryService()

    def health(self, model_id: str) -> ModelHealthStatus | None:
        model = self.registry.get_model(model_id)
        if model is None:
            return None
        latest = self._latest_result(model_id)
        if latest is None:
            return ModelHealthStatus(model_id=model_id, status="unknown", warnings=["doctor_not_run"])
        return ModelHealthStatus(
            model_id=model_id,
            status=str(latest.get("status", "unknown")),
            latest_doctor_run_id=str(latest.get("doctor_run_id")) if latest.get("doctor_run_id") else None,
            blocked_reasons=[str(item) for item in latest.get("blocked_reasons", []) or []],
            warnings=[str(item) for item in latest.get("warnings", []) or []],
        )

    def _latest_result(self, model_id: str) -> dict[str, object] | None:
        if not self.store_dir.exists():
            return None
        candidates = sorted(self.store_dir.glob(f"doctor_*_{model_id}.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            candidates = sorted(self.store_dir.glob(f"doctor_*{model_id}*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in candidates:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        return None

    def status(self) -> dict[str, object]:
        runtime = self.registry.runtime_models()
        health = [self.health(model.model_id).model_dump() for model in runtime if self.health(model.model_id)]
        return {"status": "ok", "service": "model_health", "models": health}
