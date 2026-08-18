from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.manual_inference_result import ManualInferenceResult
from aipinho.schemas.models.smoke_test_audit import SmokeTestAuditEvent
from aipinho.services.models.model_output_sanitizer import ModelOutputSanitizer
from aipinho.utils.yaml_loader import load_yaml_file


class SmokeTestAuditService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None, sanitizer: ModelOutputSanitizer | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "real_inference_run_store.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.sanitizer = sanitizer or ModelOutputSanitizer()

    def record(self, result: ManualInferenceResult) -> SmokeTestAuditEvent:
        event = SmokeTestAuditEvent(
            run_id=result.run_id,
            profile_id=result.profile_id,
            provider_id=result.provider_id,
            model_id=result.model_id,
            real_inference=result.real_inference,
            process_started=result.process_started,
            status=result.status,
            duration_ms=result.duration_ms,
            blocked_reasons=list(result.violations),
            warnings=list(result.warnings),
        )
        audit_path = PATHS.project_root / str(self.config.get("store", {}).get("audit_log", "data/logs/audit/manual_inference_smoke.jsonl"))
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.open("a", encoding="utf-8").write(json.dumps(event.model_dump(), ensure_ascii=True, sort_keys=True) + "\n")
        return event

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "smoke_test_audit"}
