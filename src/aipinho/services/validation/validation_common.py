from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from aipinho.schemas.validation.validation_finding import ValidationFinding

_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+")
_SENSITIVE_KEYS = {"content", "raw", "raw_content", "full_prompt", "prompt", "model_output", "full_model_output", "password", "secret", "token", "api_key"}


def as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def sanitize(value: Any, *, key: str = "", max_string_chars: int = 30000) -> Any:
    if key.lower() in _SENSITIVE_KEYS:
        return "[omitted_by_validation_store]"
    if isinstance(value, dict):
        return {str(k): sanitize(v, key=str(k), max_string_chars=max_string_chars) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(item, max_string_chars=max_string_chars) for item in value]
    if isinstance(value, str):
        return _SECRET_PATTERN.sub("[REDACTED]", value)[:max_string_chars]
    return value


def contains_secret(value: Any) -> bool:
    text = str(value)
    return bool(_SECRET_PATTERN.search(text))


def finding(code: str, title: str, message: str, *, severity: str = "warning", validator: str = "validation", evidence: list[str] | None = None, blocking: bool | None = None) -> ValidationFinding:
    sev = severity if severity in {"info", "warning", "error", "critical"} else "warning"
    return ValidationFinding(
        finding_id=f"validation_finding_{uuid4().hex}",
        code=code,
        title=title,
        severity=sev,  # type: ignore[arg-type]
        message=message,
        evidence=list(evidence or []),
        validator=validator,
        blocking=bool(blocking if blocking is not None else sev in {"error", "critical"}),
    )


def collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.append(str(key))
            out.extend(collect_strings(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(collect_strings(item))
        return out
    if value is None:
        return []
    return [str(value)]
