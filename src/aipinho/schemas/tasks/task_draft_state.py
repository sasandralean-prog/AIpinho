from __future__ import annotations

from typing import Literal

TaskDraftStatus = Literal[
    "draft",
    "needs_clarification",
    "blocked",
    "preview_ready",
    "approval_required",
    "ready_for_approval",
    "approval_pending",
    "approved_for_future_execution",
    "rejected",
    "cancelled",
    "expired",
    "invalidated_by_policy_change",
    "deleted",
]
WorkspaceDraftStatus = Literal["missing", "candidate", "confirmed", "protected", "not_required"]
