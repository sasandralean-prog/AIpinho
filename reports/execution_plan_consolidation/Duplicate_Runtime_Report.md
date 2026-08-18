# Duplicate Runtime Report

## Duplications Consolidated

### Planning To Execution Boundary

`TaskRunPlanner` and `PlannerV2` now both attach the same canonical concepts:

- CandidatePlan
- CanonicalExecutionPlan

This avoids creating separate execution-boundary shapes for planner generations.

### Approval Binding

Approval is now bound through `execution_id` and `execution_plan_snapshot`.

This reduces competing approval anchors such as task-only, patch-only or preview-only approval semantics.

### Timeline State

Canonical events are emitted through the existing TaskRunEventService and existing event policy.

No separate timeline repository was created.

## Duplications Still Present For Compatibility

These remain intentionally, pending broader migration:

- legacy snake_case events alongside canonical PascalCase events;
- read-only tool execution service separate from TaskRun execution;
- preview executable-plan references used by older approval flows;
- historical patch planning concepts separate from CanonicalExecutionPlan.

## Recommendation

Future cleanup should remove compatibility duplicates only after all public consumers read:

- `CanonicalExecutionPlan`;
- `execution_id`;
- Universal Task Session timeline;
- canonical completion and Speaker Truth outputs.
