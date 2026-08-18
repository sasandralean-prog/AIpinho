from __future__ import annotations

import json
import re
from typing import Any


class ProjectProfileSecretScanner:
    _PATTERNS = [
        re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|cookie|bearer)\b\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
        re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
        re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]

    def scan(self, payload: Any) -> list[str]:
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        findings: list[str] = []
        for pattern in self._PATTERNS:
            if pattern.search(text):
                findings.append(pattern.pattern)
        return findings


def has_profile_secret_risk(payload: Any) -> bool:
    return bool(ProjectProfileSecretScanner().scan(payload))

