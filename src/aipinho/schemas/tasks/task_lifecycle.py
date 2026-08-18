from __future__ import annotations

from typing import Literal

TaskDraftLifecycleStatus = Literal[
    "draft",
    "needs_clarification",
    "blocked",
    "preview_ready",
    "approval_required",
    "approval_pending",
    "approved_for_future_execution",
    "rejected",
    "cancelled",
    "expired",
    "invalidated_by_policy_change",
]