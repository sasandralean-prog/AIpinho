# ExecutionPlan Architecture Report

## Scope

This consolidation introduces `CanonicalExecutionPlan` as the execution boundary for governed runtime work.

The boundary is intentionally narrow:

- It represents future execution.
- It does not represent prompt interpretation.
- It does not represent a user-facing answer.
- It does not represent a patch plan.
- It is serializable and independent from service classes.

## Canonical Flow

Current governed runtime path:

1. TaskRunRequest is planned.
2. Planning output is converted to a CandidatePlan.
3. Effective policy snapshot promotes or rejects the CandidatePlan.
4. A CanonicalExecutionPlan is bound to task_id, taskrun_id and approval_id.
5. TaskRunGuard refuses execution without a canonical plan.
6. Approval binding is validated against execution_id.
7. SupervisedExecutionLoop executes only after the plan boundary exists.
8. Timeline records canonical execution events alongside legacy events.
9. Speaker Truth can derive final state from timeline, validation, artifacts and completion.

Execution runners consume the ExecutionPlan goal and step inputs instead of raw prompt/session text.

## Canonical Contracts Added

Implemented in:

- `src/aipinho/schemas/runtime/execution_plan.py`

Contracts:

- `CanonicalExecutionStep`
- `CandidatePlan`
- `CanonicalExecutionPlan`
- `ExecutionPlanPromotionDecision`
- `CanonicalExecutionPlanSerializer`

## Runtime Services Added

Implemented in:

- `src/aipinho/services/runtime/execution_plan_promotion_service.py`

Responsibilities:

- Build CandidatePlan from existing TaskRunPlan.
- Promote CandidatePlan through policy snapshot.
- Reject structurally unsafe side-effect plans.
- Bind runtime identity after Universal Task bootstrap.

## Architecture Decision

The consolidation did not create a second executor or dispatcher. Existing TaskRun planning and supervised execution now pass through the ExecutionPlan boundary.

Legacy planners that still return only `TaskRunPlan` are promoted by `TaskRuntimeService` before a run can execute.

## Validation

Validated command:

```text
python -m pytest tests/unit/test_execution_plan_promotion_service.py tests/unit/test_task_runtime_service.py tests/unit/test_runtime_operator_ro.py tests/unit/test_planner_v2.py tests/unit/test_runtime_timeline_service.py tests/unit/test_workflow_truth_runtime.py tests/unit/test_task_bootstrap_runtime_service.py tests/unit/test_universal_approver_layer.py tests/contract/test_read_only_execution_contracts.py tests/integration/test_read_only_execution_api.py tests/governance/test_g20_context_discovery_gate.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_canonical_lifecycle_trace.py tests/contract/test_task_runtime_contracts.py tests/unit/test_task_run_guard.py tests/unit/test_supervised_execution_loop.py -q
```

Result:

```text
111 passed
```
