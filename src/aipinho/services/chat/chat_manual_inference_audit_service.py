from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.services.models.model_output_sanitizer import ModelOutputSanitizer
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class ChatManualInferenceAuditService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None, sanitizer: ModelOutputSanitizer | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "chat" / "chat_inference_audit_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.sanitizer = sanitizer or ModelOutputSanitizer()

    @property
    def audit_config(self) -> dict[str, Any]:
        value = self.config.get("audit", {})
        return value if isinstance(value, dict) else {}

    def record(self, *, event_type: str, request: Any | None = None, response: Any | None = None, gate_decision: dict[str, Any] | None = None, warnings: list[str] | None = None) -> dict[str, object]:
        cfg = self.audit_config
        event = {
            "audit_event_id": f"manual_chat_audit_{uuid4().hex}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "session_id": getattr(request, "session_id", None),
            "profile_id": getattr(request, "profile_id", None),
            "model_id": getattr(request, "model_id", None),
            "provider_id": getattr(request, "provider_id", None),
            "allow_real_inference": bool(getattr(request, "allow_real_inference", False)),
            "operator_confirmed": bool(getattr(request, "operator_confirmed", False)),
            "process_started": bool(getattr(response, "process_started", False)) if response is not None else False,
            "real_inference": bool(getattr(response, "real_inference", False)) if response is not None else False,
            "status": getattr(response, "status", None),
            "gate_status": gate_decision.get("status") if isinstance(gate_decision, dict) else None,
            "blocked_reasons": gate_decision.get("blocked_reasons", []) if isinstance(gate_decision, dict) else [],
            "warnings": list(dict.fromkeys(warnings or [])),
        }
        if cfg.get("persist_sanitized_preview", True):
            prompt = getattr(request, "message", "") if request is not None else ""
            output = getattr(response, "message", "") if response is not None else ""
            event["prompt_preview"] = self.sanitizer.sanitize(prompt, max_chars=int(cfg.get("max_prompt_preview_chars", 160) or 160))
            event["output_preview"] = self.sanitizer.sanitize(output, max_chars=int(cfg.get("max_output_preview_chars", 240) or 240))
        if cfg.get("enabled", True):
            self._append(event)
        return event

    def _append(self, event: dict[str, object]) -> None:
        rel = str(self.audit_config.get("audit_log", "data/logs/audit/manual_chat_inference.jsonl"))
        path = resolve_within_root(PATHS.project_root / rel, PATHS.project_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "chat_manual_inference_audit", "persist_full_prompt": bool(self.audit_config.get("persist_full_prompt", False)), "persist_full_output": bool(self.audit_config.get("persist_full_output", False))}
