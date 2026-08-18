from __future__ import annotations

from typing import Literal

ArtifactDraftStatus = Literal["draft", "blocked"]
ArtifactPreviewStatus = Literal[
    "preview_ready",
    "blocked",
    "needs_approval",
    "approval_pending",
    "approved_for_future_write",
    "rejected",
    "cancelled",
    "expired",
    "invalidated",
]
ArtifactRiskLevel = Literal["low", "medium", "high", "critical"]
ArtifactSourceType = Literal[
    "project_report",
    "task_run_result",
    "validation_result",
    "role_pipeline_run",
    "user_provided_content",
    "deterministic_export",
]
ArtifactFormat = Literal["markdown", "text", "json", "yaml", "csv", "html", "unknown"]
