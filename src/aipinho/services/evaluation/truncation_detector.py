from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class TruncationDetector:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "evaluation" / "truncation_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def detect(self, content: str, model_response: dict[str, Any] | None = None) -> dict[str, object]:
        model_response = model_response or {}
        reasons: list[str] = []
        text = content or ""
        if model_response.get("finish_reason") == "length":
            reasons.append("finish_reason_length")
        stripped = text.strip()
        if not stripped:
            reasons.append("empty_output")
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                json.loads(stripped)
            except json.JSONDecodeError:
                reasons.append("incomplete_json")
        if stripped.count("```") % 2 == 1:
            reasons.append("unclosed_markdown_fence")
        if len(stripped) > 40 and stripped[-1:] not in {".", "!", "?", "`", "}", "]"}:
            reasons.append("cut_sentence")
        return {"truncation_detected": bool(reasons), "reasons": list(dict.fromkeys(reasons))}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "truncation_detector", "enabled": True}
