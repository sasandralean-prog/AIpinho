# Governance G0 Baseline

- Audit type: governance_topology_audit
- Generated UTC: 2026-06-26T07:31:34.299Z
- Checkpoint: G0_BASELINE_READY

| Case | Prompt/symptom | Evidence | Risk/meaning | Severity |
| --- | --- | --- | --- | --- |
| G0-01 | planning_readonly overcaptured as permission_grant_request | PermissionGrant parser now has readonly and negation guards, but it still runs before the operation router. | P0 |
| G0-02 | workspace permission list routed as conversation | Router and ChatService now expose workspace_permission_list, but non-chat channels may still diverge. | P1 |
| G0-03 | folder/project creation blocked without approval_id | Policy can express ask, but preview/approval depends on executable draft generation. | P0 |
| G0-04 | approved approval produced project_generation_plan_missing | Approval now validates executable plans; runtime completion/result mapping for project_generation remains a gap. | P0 |
| G0-05 | old approval hash mismatch after policy/preview change | Approval hash checks exist; UI must surface stale/superseded clearly. | P1 |
| G0-06 | read-only prompt treated as write historically | Negative constraints exist, but direct chat and persistent chat are parallel paths. | P0 |
| G0-07 | contradictory policy message | Multiple vocabularies exist: needs_approval, ask, approval_required, blocked, denied. | P1 |
| G0-08 | speaker claimed permission/success without real execution | Approval command path improved; standalone publishers still need canonical truth. | P0 |
| G0-09 | validation passed with missing outcomes | Completion policy does not cover project_generation/project_bootstrap. | P0 |
| G0-10 | preview/approval shown but list/store diverged | ApprovalService is common, but UI aggregators and chat commands are separate consumers. | P1 |

G0 conclusion: the symptoms form a lifecycle topology problem, not isolated prompt bugs.
