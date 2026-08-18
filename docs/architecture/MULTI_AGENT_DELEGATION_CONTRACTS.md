# Multi-Agent Delegation Contracts

## Purpose

Sprint 5 adds governed agent-to-agent delegation for the AIpinho multi-agent kernel.
Delegation is not a shortcut around policy, tools, approval, validation, or event traces.
It creates a parent/child run relationship so one agent can request another agent's capability while keeping source of truth, timeline and policy decisions auditable.

## Canonical Flow

1. Parent agent receives or owns a run.
2. Parent creates a `DelegationCreateRequest`.
3. `AgentDelegationService` builds a `DelegationRequest`.
4. `AgentDelegationPolicyService` evaluates target agent, operation, capabilities, workspace role, risk, execution mode, depth, child count and cycle protection.
5. If denied, the delegation becomes blocked with a structured reason.
6. If approval is required, the parent run moves to `pending_approval` and no child run is created.
7. If allowed or auto-approved, a child run is created for the target agent.
8. Child run receives `parent_run_id` and `delegation_id`.
9. Parent run enters `delegation_running` / `waiting_child_run` state.
10. Tool Gateway invocations from the child preserve `parent_run_id` and `delegation_id`.
11. Events, artifacts and evidence refs keep the delegation trace visible without exposing raw data by default.

## Schemas

- `DelegationCreateRequest`: user goal, target agent, requested operation, capabilities, workspace, risk, timeout and metadata.
- `DelegationRequest`: immutable delegation contract with parent agent/run/session and optional child run/session.
- `DelegationPolicyDecision`: policy decision, reason code, approval requirement, autoapproval id and safe alternative.
- `DelegationResult`: outcome, evidence refs, child run, artifacts, validation id and sanitized metadata.
- Tool Gateway records now carry optional `parent_run_id` and `delegation_id`.

## Policy

`config/agents/delegation_policy.yaml` is the source of delegation rules. The service does not use prompt-specific, path-specific, sprint-specific or user-specific logic.

Policy controls:

- enabled parent/target routes;
- allowed operations;
- allowed capabilities;
- denied capabilities;
- workspace roles;
- risk levels;
- execution modes;
- autoapproval;
- approval escalation;
- max delegation depth;
- max children per parent run;
- timeout limits;
- cycle detection.

## Endpoints

- `POST /api/v1/agents/{agent_id}/runs/{run_id}/delegate`
- `GET /api/v1/agents/delegations/{delegation_id}`
- `GET /api/v1/agents/delegations/{delegation_id}/events`
- `GET /api/v1/agents/delegations/{delegation_id}/result`
- `POST /api/v1/agents/delegations/{delegation_id}/cancel`
- `POST /api/v1/agents/delegations/{delegation_id}/check-timeout`
- `GET /api/v1/agents/runs/{run_id}/children`
- `GET /api/v1/agents/runs/{run_id}/parent`

## Event Types

- `delegation_created`
- `delegation_policy_checked`
- `delegation_auto_approved`
- `delegation_accepted`
- `delegation_child_run_started`
- `delegation_blocked`
- `delegation_approval_required`
- `delegation_cancelled`
- `delegation_timed_out`
- `delegation_completed`
- `delegation_failed`

## Safety Model

Delegation preserves governed operational freedom. Safe low/medium risk delegations can auto-run when the route and execution mode allow it. High-risk or ambiguous actions require approval. Critical or forbidden actions are denied. Tool execution remains subject to Tool Gateway, Policy Kernel, workspace policy, shell policy and validation.

## Known Limits

- Approval consumption for a pending delegation is a follow-up integration with the broader approval UI.
- Child run execution is established as a governed contract and run lineage; specialized agent workers still decide actual domain execution in later sprints.
- UI was not changed in Sprint 5.
