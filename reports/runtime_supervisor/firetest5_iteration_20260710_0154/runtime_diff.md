# Runtime Diff Summary

This report summarizes the functional diff without relying on git metadata.

## Public Runtime API Schema

Added public response fields for runtime execution evidence:

- runtime_result
- task_id
- task_run_id
- operation_id
- artifact_ids
- validation_state
- completion_state
- speaker_truth_state

## Public Runtime API Service

Added `PublicRuntimeExecutionBridge`.

The bridge detects executable contracts through structured capabilities and routes supported read-only artifact analysis into canonical runtime execution.

## Read-only Artifact Runtime

Added request workspace context extraction and propagation into:

- TaskRun intent_map
- Artifact provenance
- Artifact content metadata

## Runtime Operator

Snapshot by `task_run_id` now loads the real TaskRun store, timeline and truth engine instead of returning empty observations.

## Tests

Added regression coverage for public runtime execution and TaskRun snapshot hydration.
