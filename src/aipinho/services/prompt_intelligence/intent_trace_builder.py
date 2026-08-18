from __future__ import annotations

from aipinho.schemas.policy.policy_trace import PolicyTraceItem
from aipinho.services.policy_kernel.policy_trace_service import PolicyTraceService


class IntentTraceBuilder:
    def __init__(self, trace_service: PolicyTraceService | None = None) -> None:
        self.trace_service = trace_service or PolicyTraceService()

    def item(self, *, stage: str, rule: str, decision: str, reason: str, source: str, input: dict[str, object] | None = None, severity: str = "info") -> PolicyTraceItem:
        return self.trace_service.create(
            stage=stage,
            rule=rule,
            decision=decision,
            reason=reason,
            severity=severity,  # type: ignore[arg-type]
            source=source,
            input=input or {},
        )