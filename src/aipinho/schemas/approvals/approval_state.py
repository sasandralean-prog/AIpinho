from __future__ import annotations

from typing import Literal

ApprovalStatus = Literal["pending", "approved", "rejected", "cancelled", "expired", "invalidated_by_policy_change"]
ApprovalDecisionValue = Literal["approved", "rejected", "cancelled"]
ApprovalScope = Literal["preview", "execution_plan", "future_execution", "future_artifact_write", "artifact_write_execute", "patch_apply", "curated_memory_persist", "single_action", "safe_batch", "full_task_limited"]
