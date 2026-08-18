from __future__ import annotations

from aipinho.schemas.policy.policy_trace import PolicyTraceItem, Severity


class PolicyTraceService:
    def create(
        self,
        *,
        stage: str,
        rule: str,
        decision: str,
        reason: str,
        severity: Severity = "info",
        source: str,
        input: dict[str, object] | None = None,
    ) -> PolicyTraceItem:
        return PolicyTraceItem(
            stage=stage,
            rule=rule,
            decision=decision,
            reason=reason,
            severity=severity,
            source=source,
            input=input or {},
        )