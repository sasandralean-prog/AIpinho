from __future__ import annotations


class TaskLifecycleService:
    VALID_TRANSITIONS = {
        "draft": {"preview_ready", "approval_required", "needs_clarification", "blocked", "cancelled", "expired"},
        "needs_clarification": {"preview_ready", "approval_required", "blocked", "cancelled", "expired"},
        "preview_ready": {"approval_pending", "cancelled", "expired", "invalidated_by_policy_change"},
        "approval_required": {"approval_pending", "rejected", "cancelled", "expired", "invalidated_by_policy_change"},
        "approval_pending": {"approved_for_future_execution", "rejected", "cancelled", "expired", "invalidated_by_policy_change"},
        "blocked": set(),
        "approved_for_future_execution": set(),
        "rejected": set(),
        "cancelled": set(),
        "expired": set(),
        "invalidated_by_policy_change": set(),
    }

    def can_transition(self, current: str, target: str) -> bool:
        return target in self.VALID_TRANSITIONS.get(current, set()) or current == target

    def next_for_preview(self, preview_status: str) -> str:
        if preview_status == "preview_ready":
            return "preview_ready"
        if preview_status == "approval_required":
            return "approval_required"
        if preview_status == "blocked":
            return "blocked"
        if preview_status == "needs_clarification":
            return "needs_clarification"
        return "invalidated_by_policy_change"