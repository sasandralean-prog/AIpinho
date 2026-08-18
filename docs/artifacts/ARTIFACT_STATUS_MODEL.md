# Artifact Status Model

Tool artifacts now expose a status field suitable for UI rendering and download gating.

Statuses:

- `requested`
- `generating`
- `validating`
- `ready`
- `failed`
- `blocked`
- `expired`
- `deleted`

Only `ready` artifacts should show a normal download action. Other statuses must render as progress, failure, block or unavailable states.

Additional metadata fields:

- `size_bytes`
- `validation_id`
- `sandbox_task_id`
- `project_generation_id`
- `error_reason`
- `evidence_refs`

Artifacts remain token-protected. Token values are never placed in URLs.

