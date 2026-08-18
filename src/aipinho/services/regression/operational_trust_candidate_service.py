from __future__ import annotations

from typing import Any

from aipinho.schemas.regression.contracts import RegressionCaseCandidate
from aipinho.services.events.event_core import redact_payload
from aipinho.services.regression.regression_core import RegressionCandidateService


class OperationalTrustCandidateService:
    CRITICAL_CATEGORIES = {
        "write_allowed_incorrectly",
        "write_blocked_incorrectly",
        "dangerous_shell_allowed",
        "speaker_truth_false",
        "mobile_false_healthy_state",
        "validation_gate_inconsistent",
        "policy_capability_conflict",
        "artifact_lifecycle_broken",
        "event_contract_missing",
        "task_stale_reused",
    }

    def __init__(self, candidates: RegressionCandidateService | None = None) -> None:
        self.candidates = candidates or RegressionCandidateService()

    def create_for_failure(
        self,
        *,
        category: str,
        source: str,
        expected_behavior: dict[str, Any],
        observed_behavior: dict[str, Any],
        severity: str = "high",
        snapshot_id: str | None = None,
    ) -> RegressionCaseCandidate:
        safe_category = category if category in self.CRITICAL_CATEGORIES else "policy_capability_conflict"
        evidence = [
            {
                "source": source,
                "category": safe_category,
                "observed_behavior": self._redact(observed_behavior),
            }
        ]
        expected = {
            "source": source,
            "category": safe_category,
            "expected_behavior": self._redact(expected_behavior),
        }
        return self.candidates.create(
            source_type=source,
            category=safe_category,
            severity=severity,
            evidence=evidence,
            expected_behavior=expected,
            snapshot_id=snapshot_id,
        )

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "operational_trust_candidate",
            "critical_categories": sorted(self.CRITICAL_CATEGORIES),
        }

    def _redact(self, payload: Any) -> Any:
        redacted = redact_payload(payload)
        if isinstance(redacted, dict):
            safe: dict[str, Any] = {}
            for key, value in redacted.items():
                lowered = str(key).lower()
                if any(marker in lowered for marker in ("token", "secret", "password", "credential", "api_key")):
                    safe[str(key)] = "[REDACTED]"
                else:
                    safe[str(key)] = self._redact(value)
            return safe
        if isinstance(redacted, list):
            return [self._redact(item) for item in redacted]
        return redacted
