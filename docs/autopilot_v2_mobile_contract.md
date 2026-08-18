# Autopilot v2 Mobile View-Model Contract

Endpoint:

`GET /api/v1/mobile/view-model/workflows`

Purpose:

Expose current workflow status to Mobile without raw logs by default.

## Payload Shape

```json
{
  "state": {
    "screen": "workflows",
    "status": "ok",
    "raw_default_visible": false,
    "human_summary": "Workflows Autopilot v2 com plano, checkpoints e evidencias."
  },
  "active_workflow": {},
  "runs": [],
  "pending_approvals": [],
  "actions": []
}
```

## Rules

- `raw_default_visible` must remain false.
- Pending approvals must be visible without exposing secrets.
- Actions are endpoint hints for UX only; policy is decided by backend.
- Mobile must not invent workflow status.
- Mobile must treat terminal statuses as historical.

## User Actions

The initial action set is:

- pause workflow;
- resume workflow;
- cancel workflow;
- view plan;
- view checkpoints;
- open trace/debugger.

Approval buttons should use the workflow approval endpoints and display the workflow risk/evidence before approval.
