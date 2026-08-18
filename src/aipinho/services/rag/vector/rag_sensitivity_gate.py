from __future__ import annotations

import re

from aipinho.services.rag.vector.config import rag_config


class RAGSensitivityGate:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or rag_config("rag_sensitivity_policy.yaml")

    def check(self, text: str, *, source_type: str | None = None) -> dict[str, object]:
        blocked: list[str] = []
        warnings: list[str] = []
        lowered = text.lower()
        if source_type in {"raw_log", "raw_logs"} or "raw log" in lowered or "raw_log" in lowered:
            blocked.append("raw_log_ingestion_blocked")
        policy = self.config.get("sensitivity", {}) if isinstance(self.config.get("sensitivity", {}), dict) else {}
        for pattern in policy.get("patterns", []) or []:
            if re.search(str(pattern), text):
                blocked.append("secret_or_sensitive_content_blocked")
                break
        return {"allowed": not blocked, "status": "ok" if not blocked else "blocked", "warnings": warnings, "blocked_reasons": blocked}

    def redact(self, text: str) -> str:
        redacted = re.sub(r"(?i)(api[_-]?key|password|token)\s*[:=]\s*\S+", r"\1=<redacted>", text)
        return re.sub(r"-----BEGIN .*PRIVATE KEY-----.*?-----END .*PRIVATE KEY-----", "<redacted_private_key>", redacted, flags=re.DOTALL)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_sensitivity_gate", "secret_ingestion_blocked": True, "raw_log_ingestion_blocked": True}
