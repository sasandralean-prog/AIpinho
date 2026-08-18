
# G9 Canonical Preview Approval Report

- Generated UTC: 2026-06-26T09:00:00.641106+00:00
- Mode: consolidated canonical core, not route adapter
- Functional route rewire: not performed in this checkpoint


Checkpoint: `G9_CANONICAL_PREVIEW_APPROVAL_READY`

Implemented:
- `CanonicalApprovalService`
- preview kinds: `plan_only_preview` and `executable_task_preview`.
- approval can be created only when policy is `ask` and execution plan is executable with `executable_plan_ref`.
- approval is not created for missing executable plan.

Validation covered:
- `ask` without executable plan returns `approval_not_created_no_executable_plan`.
- `ask` with executable plan returns `pending_approval`.
