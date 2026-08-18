# Autopilot v2 Workflows

Autopilot v2 is the governed multi-step workflow layer for AIpinho.

It does not replace agents, policies, approvals, Tool Gateway, Sandbox, Promotion, Artifact Library, Validation or Learning Memory. It coordinates those services through an auditable workflow contract:

1. workflow plan
2. workflow run
3. phases and steps
4. checkpoints
5. approvals when risk requires them
6. governed execution
7. validation
8. final report
9. memory candidates

## Core Contracts

- `WorkflowPlan`: declarative plan. It never executes by itself.
- `WorkflowRun`: execution state for a plan.
- `WorkflowPhase`: grouped workflow phase such as intake, planning, execution, validation or reporting.
- `WorkflowStep`: governed action inside a phase.
- `WorkflowCheckpoint`: resumable state snapshot before/after important moments.
- `WorkflowRecoveryPlan`: structured recovery proposal for failures.
- `WorkflowFinalReport`: final truth artifact for the run.

## Policy

The runtime policy lives in `config/autopilot/workflow_policy.yaml`.

The policy keeps these invariants:

- plans are required before execution;
- checkpoints are required around side effects and validation;
- approvals are required for medium/high risk and promotion apply;
- source-readonly writes are denied;
- artifacts are token-protected;
- raw and secrets are not exported;
- memory entries are candidates, not auto-accepted global facts.

## Execution Model

Autopilot v2 can:

- plan sandbox creation;
- pause on external workspace onboarding;
- coordinate sandbox task execution;
- coordinate promotion workflows;
- emit evidence and artifacts;
- generate final reports;
- propose learning memory candidates.

It cannot bypass policy, approval or validation gates.

## Endpoints

- `POST /api/v1/workflows/plans`
- `GET /api/v1/workflows/plans`
- `GET /api/v1/workflows/plans/{workflow_plan_id}`
- `POST /api/v1/workflows/runs`
- `GET /api/v1/workflows/runs`
- `GET /api/v1/workflows/runs/{workflow_run_id}`
- `POST /api/v1/workflows/runs/{workflow_run_id}/pause`
- `POST /api/v1/workflows/runs/{workflow_run_id}/resume`
- `POST /api/v1/workflows/runs/{workflow_run_id}/cancel`
- `GET /api/v1/workflows/runs/{workflow_run_id}/approvals`
- `POST /api/v1/workflows/runs/{workflow_run_id}/approvals/{approval_id}/approve`
- `POST /api/v1/workflows/runs/{workflow_run_id}/approvals/{approval_id}/reject`
- `GET /api/v1/workflows/runs/{workflow_run_id}/checkpoints`
- `GET /api/v1/workflows/checkpoints/{checkpoint_id}`
- `POST /api/v1/workflows/runs/{workflow_run_id}/recover`
- `GET /api/v1/workflows/recovery/{recovery_plan_id}`
- `POST /api/v1/workflows/runs/{workflow_run_id}/report`
- `GET /api/v1/workflows/runs/{workflow_run_id}/trace`

## Validation

Sprint 35 validation:

- `python -m py_compile ...` passed.
- `python -m pytest tests\workflows -q --durations=10` passed: 6 tests.
- `python tests\multi_agent\run_multi_agent_regression.py --workflows` passed: 6 tests.

## Current Limits

- Workflow v2 stores state in local JSON runtime files.
- Dedicated Launcher/Mobile visual workflow cockpit remains a UX follow-up.
- Recovery is conservative: preserve evidence, partial report, resume/stop safely.
- Real long-running background worker orchestration is not expanded in this sprint.
