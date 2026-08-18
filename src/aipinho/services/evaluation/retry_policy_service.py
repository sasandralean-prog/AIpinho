from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.evaluation.retry_decision import RetryDecision
from aipinho.utils.yaml_loader import load_yaml_file


class RetryPolicyService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "evaluation" / "retry_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def decide(self, violations: list[str], *, truncation_detected: bool = False, attempts: int = 0) -> RetryDecision:
        retry = self.config.get("retry", {}) if isinstance(self.config.get("retry", {}), dict) else {}
        max_retries = int(retry.get("max_retries", 1) or 1)
        if not retry.get("enabled", True) or attempts >= max_retries:
            return RetryDecision(should_retry=False, reason="retry_disabled_or_exhausted", max_retries=max_retries)
        do_not_retry = set(str(item) for item in retry.get("do_not_retry_on", []) or [])
        for violation in violations:
            if violation in do_not_retry or any(item in violation for item in do_not_retry):
                return RetryDecision(should_retry=False, reason=violation, max_retries=max_retries)
        retry_on = set(str(item) for item in retry.get("retry_on", []) or [])
        strategies = retry.get("retry_strategy", {}) if isinstance(retry.get("retry_strategy", {}), dict) else {}
        retryable_truncation = truncation_detected and any(item in violations for item in {"truncation", "invalid_json"})
        normalized = ["truncation" if retryable_truncation else "", *violations]
        for reason in normalized:
            if not reason:
                continue
            for candidate in retry_on:
                if candidate in reason or (candidate == "truncation" and truncation_detected):
                    return RetryDecision(
                        should_retry=True,
                        reason=candidate,
                        strategy=str(strategies.get(candidate, candidate)),
                        max_retries=max_retries,
                        retry_prompt_hint=self._hint(candidate),
                    )
        return RetryDecision(should_retry=False, reason="not_retryable", max_retries=max_retries)

    def _hint(self, reason: str) -> str:
        return {
            "invalid_json": "Return only valid JSON matching the requested fields.",
            "truncation": "Reduce scope and complete the response without truncation.",
            "missing_required_section": "Include every required section from the output contract.",
        }.get(reason, "Retry with stricter output contract compliance.")

    def status(self) -> dict[str, object]:
        retry = self.config.get("retry", {}) if isinstance(self.config.get("retry", {}), dict) else {}
        return {"status": "ok", "service": "retry_policy", "enabled": bool(retry.get("enabled", True)), "max_retries": int(retry.get("max_retries", 1) or 1)}

