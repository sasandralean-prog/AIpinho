# Governance Block A Recommendations

- Audit type: governance_topology_audit
- Generated UTC: 2026-06-26T07:31:34.299Z

## Objective for Block B

Create a canonical governed execution path without deleting legacy in one large cutover.

## Proposed sequence

1. Canonical IntentDecision with precedence table and negative constraints.
2. Canonical OperationContract normalization for action/workspace/risk.
3. Single permission resolver output enum: allowed, ask, denied.
4. Preview builder emits plan_only_preview or executable_task_preview.
5. ApprovalRequest targets only executable draft or explicit non-execution approval.
6. TaskRun starts only from approved executable draft.
7. Completion resolver and validation gate share required outcomes.
8. Speaker Truth reads only from final lifecycle snapshot.
9. All channels call the same facade; old routes become adapters.

## Regression gates

- planning/read-only prompts never create grants, approvals, tasks, or writes.
- positive session grant creates temporary grant or approves compatible pending approval.
- workspace permission query returns registry data, never generic conversation.
- folder/project creation under ask creates preview plus approval with real target paths.
- approval cannot be created without executable plan.
- approved executable plan creates TaskRun with required outcomes.
- blocked run produces blocked message, not success.
- validation cannot pass when required outcomes are missing.
- all channels produce the same lifecycle for the same prompt class.

## Do not do in Block B

- Do not delete legacy before adapters exist.
- Do not loosen policy by bypassing permission checks.
- Do not hardcode LogForge, AIpinho Studio, PinhoForge, paths, or prompt phrases.
- Do not let UI decide policy.
- Do not declare READY from preview-only state.

## First patch target

Start with an adapter-only GovernanceLifecycleService that returns a lifecycle snapshot. Wire one low-risk route first, compare direct chat versus persistent chat, then migrate other channels.
