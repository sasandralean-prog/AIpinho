# Canonical Runtime Diff

## Files Added

- `src/aipinho/schemas/runtime/execution_plan.py`
- `src/aipinho/services/runtime/execution_plan_promotion_service.py`
- `tests/unit/test_execution_plan_promotion_service.py`

## Files Updated

- `src/aipinho/schemas/runtime/task_run_plan.py`
- `src/aipinho/schemas/runtime/planner_v2.py`
- `src/aipinho/services/runtime/task_run_planner.py`
- `src/aipinho/services/runtime/planner_v2_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/task_run_guard.py`
- `src/aipinho/services/runtime/supervised_execution_loop.py`
- `src/aipinho/services/runtime/governed_task_step_runner.py`
- `src/aipinho/services/runtime/readonly_task_step_runner.py`
- `src/aipinho/schemas/approvals/approval_state.py`
- `src/aipinho/schemas/approvals/approval_request.py`
- `src/aipinho/services/approvals/approval_service.py`
- `src/aipinho/api/routers/tool_execution_router.py`
- `config/runtime/task_run_event_policy.yaml`
- `config/runtime/task_speaker_update_policy.yaml`
- `tests/support/runtime_fixtures.py`
- `tests/unit/test_task_runtime_service.py`
- `tests/unit/test_runtime_timeline_service.py`

## Runtime Diffs

Before:

- TaskRunPlan could be executed without a canonical ExecutionPlan.
- Approval could be associated with future execution, preview or patch references.
- Timeline had no explicit ExecutionPlan boundary events.
- Legacy planners could bypass canonical promotion if they returned a plain TaskRunPlan.

After:

- TaskRuntimeService promotes every plan to CanonicalExecutionPlan.
- TaskRunGuard blocks missing plan or approval-plan mismatch.
- Approval records can bind to execution_id.
- Governed execution uses ExecutionPlan semantic_goal instead of raw prompt/session text.
- Read-only report execution consumes ExecutionPlan metadata instead of raw intent_map.
- Timeline records planning and execution boundary events.
- Public read-only status remains compatible while using canonical service status.

## Compatibility Preserved

Legacy events are still emitted:

- `run_created`
- `task_bootstrap_created`
- `run_started`
- `step_started`
- `step_completed`
- `task_completion_evaluated`
- `run_completed`

Canonical events are additive.
