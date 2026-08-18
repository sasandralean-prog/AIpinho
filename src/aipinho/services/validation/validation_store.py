from __future__ import annotations

import json
import re
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.validation.validation_gate_result import ValidationGateResult
from aipinho.schemas.validation.validation_trace import ValidationTraceItem
from aipinho.services.validation.validation_common import sanitize
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file

class ValidationStore:
    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "validation" / "validation_store_policy.yaml", critical=True, root=PATHS.config_root / "validation")
        configured = str(self.policy.get("validation_store", {}).get("path", "data/runtime/validations"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)

    def save_result(self, result: ValidationGateResult) -> ValidationGateResult:
        path = self._dir(result.validation_id) / "result.json"
        self._write(path, result.model_dump())
        self.save_trace(result.validation_id, result.trace)
        return result

    def get_result(self, validation_id: str) -> ValidationGateResult | None:
        data = self._read(self._dir(validation_id) / "result.json")
        return ValidationGateResult.model_validate(data) if data else None

    def save_trace(self, validation_id: str, trace: list[ValidationTraceItem]) -> None:
        self._write(self._dir(validation_id) / "trace.json", [item.model_dump() for item in trace])

    def get_trace(self, validation_id: str) -> list[ValidationTraceItem]:
        data = self._read(self._dir(validation_id) / "trace.json") or []
        return [ValidationTraceItem.model_validate(item) for item in data if isinstance(item, dict)]

    def list_results(self, *, limit: int = 100) -> list[ValidationGateResult]:
        if not self.root.exists():
            return []
        results: list[ValidationGateResult] = []
        for path in self.root.glob("*/result.json"):
            try:
                results.append(ValidationGateResult.model_validate(json.loads(path.read_text(encoding="utf-8-sig"))))
            except Exception:
                continue
        return sorted(results, key=lambda item: item.created_at, reverse=True)[: max(1, min(limit, 1000))]

    def _dir(self, validation_id: str) -> Path:
        if not re.fullmatch(r"validation_[a-f0-9]+", validation_id):
            raise ValueError("invalid_validation_id")
        return resolve_within_root(self.root / validation_id, self.root)

    def _write(self, path: Path, value) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sanitize(value), ensure_ascii=False, indent=2), encoding="utf-8")

    def _read(self, path: Path):
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def status(self) -> dict[str, object]:
        self.root.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "service": "validation_store", "path": str(self.root), "raw_content_enabled": False}
