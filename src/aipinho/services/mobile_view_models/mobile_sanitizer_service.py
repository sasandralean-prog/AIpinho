from __future__ import annotations

import re
from typing import Any


class MobileSanitizerService:
    _secret_patterns = (
        re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*['\"]?[^'\"\s,}]+"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
    )
    _user_path_pattern = re.compile(r"(?i)C:\\Users\\[^\\\s]+")

    def sanitize_text(self, value: str) -> str:
        sanitized = value
        for pattern in self._secret_patterns:
            sanitized = pattern.sub(lambda match: match.group(0).split(match.group(1), 1)[0] + match.group(1) + "=[REDACTED]" if match.groups() else "[REDACTED]", sanitized)
        return self._user_path_pattern.sub(lambda _: r"C:\Users\[REDACTED]", sanitized)

    def sanitize_map(self, values: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in values.items():
            sanitized[str(key)] = self.sanitize_value(value)
        return sanitized

    def sanitize_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return self.sanitize_text(value)
        if isinstance(value, dict):
            return {self.sanitize_text(str(key)): self.sanitize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self.sanitize_value(item) for item in value]
        return self.sanitize_text(str(value))

    def contains_secret(self, value: str) -> bool:
        return any(pattern.search(value) for pattern in self._secret_patterns)
