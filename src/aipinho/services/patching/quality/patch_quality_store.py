from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.quality.patch_quality_gate_result import PatchQualityGateResult
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class PatchQualityStore:
    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "quality" / "patch_quality_store_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "quality")
        configured = str((self.policy.get("store", {}) or {}).get("path", "data/runtime/patch_quality"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)
        self.secret_guard = SecretGuardService()

    def save_result(self, result: PatchQualityGateResult) -> PatchQualityGateResult:
        self._write(self._result_path(result.quality_id), result.model_dump())
        if result.plan_id:
            self._write(self._latest_for_plan_path(result.plan_id), {"quality_id": result.quality_id})
        if result.trace is not None:
            self._write(self._trace_path(result.quality_id), result.trace.model_dump())
        return result

    def get_result(self, quality_id: str) -> PatchQualityGateResult | None:
        data = self._read(self._result_path(quality_id))
        return PatchQualityGateResult.model_validate(data) if data else None

    def get_trace(self, quality_id: str) -> dict[str, Any] | None:
        return self._read(self._trace_path(quality_id))

    def get_latest_for_plan(self, plan_id: str) -> PatchQualityGateResult | None:
        data = self._read(self._latest_for_plan_path(plan_id))
        if not data:
            return None
        quality_id = str(data.get("quality_id", ""))
        return self.get_result(quality_id) if quality_id else None

    def list_results(self, *, plan_id: str | None = None, status: str | None = None, limit: int = 100) -> list[PatchQualityGateResult]:
        results: list[PatchQualityGateResult] = []
        root = self.root / "results"
        if not root.exists():
            return []
        for path in root.glob("patch_quality_*.json"):
            try:
                result = PatchQualityGateResult.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))
            except Exception:
                continue
            if plan_id and result.plan_id != plan_id:
                continue
            if status and result.status != status:
                continue
            results.append(result)
        return sorted(results, key=lambda item: item.created_at, reverse=True)[: max(1, min(limit, 1000))]

    def sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): self.sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            return self.secret_guard.redact(value)[0]
        return value

    def _result_path(self, quality_id: str) -> Path:
        self._validate_quality_id(quality_id)
        return resolve_within_root(self.root / "results" / f"{quality_id}.json", self.root)

    def _trace_path(self, quality_id: str) -> Path:
        self._validate_quality_id(quality_id)
        return resolve_within_root(self.root / "trace" / f"{quality_id}.trace.json", self.root)

    def _latest_for_plan_path(self, plan_id: str) -> Path:
        self._validate_plan_id(plan_id)
        return resolve_within_root(self.root / "plans" / f"{plan_id}.latest.json", self.root)

    def _validate_quality_id(self, quality_id: str) -> None:
        if not re.fullmatch(r"patch_quality_[a-f0-9]+", quality_id):
            raise ValueError("invalid_patch_quality_id")

    def _validate_plan_id(self, plan_id: str) -> None:
        if not re.fullmatch(r"patch_plan_[a-f0-9]+", plan_id):
            raise ValueError("invalid_patch_plan_id")

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
        return {"status": "ok", "service": "patch_quality_store", "path": str(self.root), "workspace_write_enabled": False}
