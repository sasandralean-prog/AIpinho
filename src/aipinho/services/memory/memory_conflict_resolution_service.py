from __future__ import annotations


class MemoryConflictResolutionService:
    def resolve(self, *, has_conflict: bool, resolution: str | None = None) -> dict[str, object]:
        if not has_conflict:
            return {"status": "resolved", "reason": "no_conflict"}
        if resolution in {"supersede_existing", "reject_candidate"}:
            return {"status": "resolved", "reason": resolution}
        return {"status": "blocked", "reason": "unresolved_conflict"}
