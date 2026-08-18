from __future__ import annotations


class CuratedMemoryStatusService:
    ALLOWED = {"active", "superseded", "expired", "rejected"}

    def can_transition(self, current: str, target: str) -> bool:
        if current == "active":
            return target in {"superseded", "expired", "rejected"}
        if current == "superseded":
            return target == "expired"
        return target == current
