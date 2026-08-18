from __future__ import annotations

from datetime import datetime, timezone


class ApprovalLifecycleService:
    TERMINAL = {"approved", "rejected", "cancelled", "expired", "invalidated_by_policy_change"}
    VALID = {
        "pending": {"approved", "rejected", "cancelled", "expired", "invalidated_by_policy_change"},
        "approved": set(),
        "rejected": set(),
        "cancelled": set(),
        "expired": set(),
        "invalidated_by_policy_change": set(),
    }

    def can_transition(self, current: str, target: str) -> bool:
        return target in self.VALID.get(current, set())

    def ensure_pending(self, status: str) -> tuple[bool, str]:
        if status != "pending":
            return False, "approval_not_pending"
        return True, "ok"

    def is_expired(self, expires_at: str) -> bool:
        try:
            expires = datetime.fromisoformat(expires_at)
        except ValueError:
            return True
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= expires