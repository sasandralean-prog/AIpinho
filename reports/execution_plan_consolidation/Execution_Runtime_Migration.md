# Execution Runtime Migration

## Migrated Boundary

`TaskRuntimeService.create_run()` now guarantees that each created TaskRun has:

- Universal Task identity.
- TaskRun identity.
- Operation identity.
- CandidatePlan.
- CanonicalExecutionPlan.
- execution_id.
- Timeline events for planning and execution plan creation.

## Legacy Planner Compatibility

If an existing planner returns `TaskRunPlan` without `canonical_execution_plan`, the runtime promotes it before execution.

This keeps compatibility while removing the execution path that previously allowed a run to start without a canonical plan.

## Approval Migration

Approval requests now support:

- `execution_id`
- `execution_plan_snapshot`

`ApprovalService.attach_runtime_context()` binds approval records to the canonical execution_id.

`TaskRunGuard` validates that a pending or approved approval belongs to the same ExecutionPlan.

## Execution Loop Migration

`SupervisedExecutionLoop` now emits canonical execution events:

- `ExecutionPlanApproved`
- `ExecutionStarted`
- `StepStarted`
- `StepFinished`
- `ValidationStarted`
- `ValidationFinished`
- `ArtifactsCreated`
- `CompletionGenerated`
- `SpeakerTruthGenerated`

Legacy events remain emitted for public API compatibility and existing timeline consumers.

## Executor Input Migration

`GovernedTaskStepRunner` no longer retrieves raw prompts or session messages to determine execution intent.

It now derives the execution objective from:

- `TaskRun.plan.canonical_execution_plan.semantic_goal`

Shell execution plans and read-only reporting metadata are copied into the ExecutionPlan during promotion and consumed from the canonical plan at execution time.

## Endpoint Compatibility

`/api/v1/tools/execution-status` now returns the read-only execution status both as canonical nested service status and as top-level compatibility fields.

This avoids duplicating status logic in the router.

## Migration Risk

Moderate.

The highest-risk change is `TaskRunGuard` now blocking runtime execution when a canonical plan is absent or an approval is not bound to the same execution_id.

Mitigation:

- Legacy TaskRunPlan is promoted automatically.
- Raw prompt/session fallback was removed from governed execution.
- Existing public events remain available.
- Existing endpoints are preserved.
