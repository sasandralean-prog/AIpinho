from __future__ import annotations

import re

_PATTERNS = [re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+", re.IGNORECASE), re.compile(r"sk-[A-Za-z0-9_-]{12,}")]


def redact(text: str | None) -> str:
    if not text:
        return ""
    result = str(text)
    for pattern in _PATTERNS:
        result = pattern.sub("[REDACTED_SECRET]", result)
    return result
