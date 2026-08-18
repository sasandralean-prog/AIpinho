# Patch Plan

## Regression

PUBLIC_RUNTIME_EXECUTION_GAP

Executable public contracts reached Gateway and Kernel, but the response stopped at `kernel_status=ready` without TaskRun, timeline, artifacts, validation, completion, or Speaker Truth.

## Generic Fix

Add a public runtime execution bridge driven by contract capabilities:

- `requires_task`
- `execution_required`
- `artifact_generation`
- `validation_required`
- `expected_outputs`
- `workspace_mutation`
- `operation_type`
- `runtime_profile`

The bridge must not use provider names, Fire Test names, or project-specific paths.

## Route

For read-only analysis contracts with artifact generation and no workspace mutation, route to the existing canonical `ReadonlyAnalysisArtifactRuntimeService`.

For executable contracts without a supported runtime route, return structured `blocked` instead of silent `accepted`.

## Tests

- Public analyze creates TaskRun and artifacts.
- Executable public contract without route is blocked, not silently accepted.
- Existing vertical slice still passes.
- Runtime Operator snapshot hydrates real TaskRun state.
