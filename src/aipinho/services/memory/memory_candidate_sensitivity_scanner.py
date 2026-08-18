from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SensitivityScanResult:
    status: str = "safe"
    reasons: list[str] = field(default_factory=list)
    redacted_text: str = ""


class MemoryCandidateSensitivityScanner:
    SECRET_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key|token|password|passwd|secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{6,})"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"sk-[A-Za-z0-9]{12,}"),
    ]

    def scan(self, text: str, *, evidence: list[Any] | None = None) -> SensitivityScanResult:
        reasons: list[str] = []
        redacted = text
        for pattern in self.SECRET_PATTERNS:
            if pattern.search(redacted):
                reasons.append("secret_like_text")
                redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        lowered = text.lower()
        if "traceback (most recent call last)" in lowered or "raw log" in lowered:
            reasons.append("raw_log_like_text")
        if text.count("\n") > 80 or len(text) > 5000:
            reasons.append("full_file_or_dump_like_content")
        evidence_text = " ".join(getattr(item, "summary", "") for item in evidence or [])
        if any(pattern.search(evidence_text) for pattern in self.SECRET_PATTERNS):
            reasons.append("secret_like_evidence")
        if any(reason.startswith("secret") for reason in reasons):
            return SensitivityScanResult(status="blocked", reasons=list(dict.fromkeys(reasons)), redacted_text=redacted)
        if reasons:
            return SensitivityScanResult(status="blocked", reasons=list(dict.fromkeys(reasons)), redacted_text=redacted[:1200])
        return SensitivityScanResult(status="safe", redacted_text=text)
