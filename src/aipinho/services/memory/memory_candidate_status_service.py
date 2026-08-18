from __future__ import annotations


class MemoryCandidateStatusService:
    ALLOWED = {"candidate", "needs_review", "blocked", "rejected", "duplicate"}

    def can_transition(self, current: str, target: str) -> bool:
        if target == "approved":
            return False
        if current == "rejected" and target not in {"rejected"}:
            return False
        return target in self.ALLOWED
