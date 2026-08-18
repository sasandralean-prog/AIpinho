from __future__ import annotations

from typing import Any


def _to_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if hasattr(item, "dict"):
        return item.dict()
    if isinstance(item, dict):
        return item
    return {"value": str(item)}


class DecisionTraceService:
    def compact(self, trace: list[Any]) -> list[dict[str, Any]]:
        compacted: list[dict[str, Any]] = []
        for item in trace:
            data = _to_dict(item)
            compacted.append({
                "stage": data.get("stage", "unknown"),
                "decision": data.get("decision", data.get("status", "unknown")),
                "reason": data.get("reason", ""),
                "source": data.get("source"),
            })
        return compacted