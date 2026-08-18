from typing import Literal

TaskRunStatus = Literal["created", "queued", "waiting_delegation", "running", "waiting_input", "completed", "partial", "failed", "cancelled", "blocked", "expired"]
TaskRunStepStatus = Literal["pending", "running", "completed", "partial", "failed", "skipped", "blocked", "cancelled"]
