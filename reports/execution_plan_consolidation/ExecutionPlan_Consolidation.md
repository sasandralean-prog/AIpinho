# ExecutionPlan Consolidation

## Canonical Implementation

Canonical schema:

- `src/aipinho/schemas/runtime/execution_plan.py`

Canonical promotion service:

- `src/aipinho/services/runtime/execution_plan_promotion_service.py`

Canonical runtime enforcement:

- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/task_run_guard.py`
- `src/aipinho/services/runtime/supervised_execution_loop.py`

## Consolidated Behavior

Every governed TaskRun now receives an ExecutionPlan before execution.

Promotion flow:

```text
TaskRunPlan
  -> CandidatePlan
  -> policy promotion
  -> CanonicalExecutionPlan
  -> TaskRunGuard
  -> SupervisedExecutionLoop
```

## No Parallel Pipeline Added

No new executor, router or planner path was introduced.

The consolidation uses:

- existing `TaskRunPlanner`;
- existing `PlannerV2` path;
- existing `TaskRuntimeService`;
- existing `TaskRunGuard`;
- existing `SupervisedExecutionLoop`;
- existing approval service;
- existing timeline event store.

## Test Coverage Added

Added:

- `tests/unit/test_execution_plan_promotion_service.py`

Coverage:

- read-only candidate promotion;
- policy denial;
- side-effect structural rejection;
- ExecutionPlan serialization.
- governed runner uses ExecutionPlan semantic_goal instead of raw prompt fallback.

## Remaining Consolidation Candidates

The following domains still contain multiple historical concepts and should be reviewed in later cleanup waves:

- old preview executable-plan references;
- read-only tool execution IDs versus TaskRun execution_id;
- historical patch plan schemas;
- task preview planning versus TaskRun planning;
- legacy snake_case timeline consumers.
