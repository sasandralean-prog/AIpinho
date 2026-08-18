from __future__ import annotations

import re

from aipinho.schemas.rag.integration.contracts import ContextInjectionItem


class ContextSensitivityGate:
    PATTERNS = (
        re.compile(r"(?i)(api[_-]?key|token|password|passwd|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{4,}"),
        re.compile(r"\bsk-[A-Za-z0-9]{8,}\b"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    )

    def validate(self, item: ContextInjectionItem) -> dict[str, object]:
        reasons: list[str] = []
        if item.source_id == "raw_logs" or item.source_type == "raw_logs":
            reasons.append("raw_log_context_blocked")
        if any(pattern.search(item.content) for pattern in self.PATTERNS):
            reasons.append("sensitive_context_blocked")
        return {"valid": not reasons, "status": "ok" if not reasons else "blocked", "blocked_reasons": reasons}

    def redact(self, value: str) -> str:
        result = value
        for pattern in self.PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_sensitivity_gate", "raw_logs_allowed": False}
