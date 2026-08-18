# Runtime Cleanup Report

Cleanup ID: 20260706T005024Z

## Verdict

RUNTIME_CLEANUP_APPLIED

## Summary

- Evidence preserved: true
- Deleted evidence: false
- Backup directory: `C:\Dev\AIpinho\reports\runtime_cleanup\20260706T005024Z\backup`
- Hygiene preview: `cleanup_preview_8bc4ef6877564d49a5e9ca03bfdb8738`

## Before

- Agent active/stale runs: 17 active, 17 stale
- Task queue visible: 1
- Pending approvals: 0
- Chat sessions: 58
- Generic session files: 240
- Agent sessions: 237
- Task draft statuses: `{'approval_pending': 234, 'approved_for_future_execution': 346, 'rejected': 20, 'approval_required': 761, 'blocked': 586, 'needs_clarification': 523, 'preview_ready': 578, 'draft': 72, 'cancelled': 6, 'ready_for_approval': 14, 'invalidated_by_policy_change': 8}`

## Actions

- RuntimeStateHygieneService applied candidates: 41
- TaskQueueService reconcile status: ok
- TaskRuns cancelled/reconciled: 1
- Approvals cancelled: 0
- TaskDrafts marked cancelled: 2182
- Chat sessions removed from active list: 58
- Chat messages removed from active store: 270
- Generic session files archived out of active store: 240

## After

- Agent active/stale runs: 0 active, 0 stale
- Task queue visible: 0
- Pending approvals: 0
- Chat sessions: 0
- Generic session files: 0
- Agent sessions: 237
- Task draft statuses: `{'cancelled': 2188, 'approved_for_future_execution': 346, 'rejected': 20, 'blocked': 586, 'invalidated_by_policy_change': 8}`

## Restoration

All active-store session cleanup was preceded by snapshots under the backup directory. TaskRuns, approvals and drafts were not deleted; they were reconciled/cancelled in-place with audit events where supported.

## Files

- `before.json`
- `after.json`
- `summary.json`
- `manifest.json`
- `task_runs_before.json`
- `task_runs_after.json`
- `approvals_before.json`
- `approvals_after.json`
- `task_drafts_before_summary.json`
- `task_drafts_after_summary.json`
