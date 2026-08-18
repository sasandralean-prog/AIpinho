from __future__ import annotations

from typing import Any


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        import json
        return json.dumps(value, indent=2, ensure_ascii=True)
    return str(value)
