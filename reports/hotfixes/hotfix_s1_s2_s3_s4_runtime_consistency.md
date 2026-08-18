# HOTFIX S1-S4 - Runtime Consistency, Artifact Binding, Workspace Binding and Validation Ordering

## Verdict

LIFECYCLE_CONSISTENCY_READY
ARTIFACT_BINDING_READY
WORKSPACE_BINDING_READY
VALIDATION_ORDERING_READY

## Scope

This hotfix consolidated runtime state and bindings without adding new product features.

Covered fixes:

- S1: canonical operation state for lifecycle/completion/validation/Speaker Truth/UI.
- S2: TaskRun-level artifact inventory with required, produced and missing artifacts.
- S3: formal multi-root WorkspaceContext with project, external and library roots.
- S4: validation/completion guards through canonical state when outputs or artifacts are missing.

## Root Causes

1. Universal Task Session, Runtime Truth and TaskRun state could derive operational status independently.
2. Artifacts existed in the registry but were not also bound to the producing TaskRun.
3. Timeline artifact lookup relied on external registries and result string scanning before using the TaskRun as canonical source.
4. WorkspaceContext represented one root well, but did not preserve auxiliary roots such as library directories.
5. Runtime Truth required workflow completion even for runtime slices that produce a complete terminal timeline without driving the workflow engine step-by-step.

## Files Changed

- `src/aipinho/schemas/runtime/canonical_operation_state.py`
- `src/aipinho/schemas/runtime/task_run.py`
- `src/aipinho/schemas/runtime/workspace_context.py`
- `src/aipinho/schemas/runtime/__init__.py`
- `src/aipinho/services/runtime/canonical_operation_state_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/workspace_context_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/runtime/runtime_timeline_service.py`
- `src/aipinho/services/runtime/runtime_truth_engine.py`
- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `tests/unit/test_runtime_consistency_bindings.py`
- `tests/governance/test_runtime_vertical_slice.py`

## Behavior Changes

- Every new TaskRun receives `canonical_state`.
- TaskRun now carries `produced_artifacts`, `required_artifacts` and `missing_artifacts`.
- Universal Task Session exposes `metadata.canonical_operation_state` and uses it for public status.
- Timeline uses `run.produced_artifacts` as the first artifact source.
- Artifact public records now fill empty runtime fields instead of leaving explicit `None` values.
- WorkspaceContext now preserves `external_roots`, `library_roots`, `readonly_flags` and `workspace_ids`.
- Completion is blocked when required outputs or required artifacts are missing.

## Tests Added or Updated

- `test_s1_universal_session_exposes_single_canonical_state`
- `test_s2_missing_required_artifact_blocks_canonical_success`
- `test_s3_workspace_context_preserves_project_and_library_roots`
- `test_s4_completion_cannot_pass_when_outputs_are_missing`
- Extended readonly vertical slice assertions for TaskRun artifact bindings and canonical state.

## Test Results

Passed:

- `python -m pytest C:\Dev\AIpinho\tests\unit\test_runtime_consistency_bindings.py C:\Dev\AIpinho\tests\governance\test_runtime_vertical_slice.py -q`
  - 10 passed
- `python -m pytest C:\Dev\AIpinho\tests\unit\test_workspace_runtime_context.py C:\Dev\AIpinho\tests\unit\test_workflow_truth_runtime.py C:\Dev\AIpinho\tests\unit\test_universal_task_session_service.py C:\Dev\AIpinho\tests\governance\test_lifecycle_core.py -q`
  - 40 passed
- `python -m py_compile ...`
  - passed for changed runtime/schema/services files.

## Residual Risks

- Older execution paths that do not use TaskRuntimeService may still need migration to populate `canonical_state`.
- UI surfaces should prefer `metadata.canonical_operation_state` where available.
- Workflow status can remain `created` for some vertical-slice runtimes; Runtime Truth now accepts this only when terminal timeline, validation and artifacts are complete.

## Final Contract

TaskRun is now the binding point for:

- canonical state;
- workspace context;
- required artifacts;
- produced artifacts;
- missing artifacts.

No workspace mutation was introduced.

## Continuation Patch - Public Route Gates

After the first S1-S4 pass, broader contract and public-chat regressions exposed two real P0 edge leaks at public entrypoints:

1. Persistent chat could create a pending approval for protected filesystem roots such as `C:\Windows\System32`.
2. Persistent chat did not surface dispatcher saturation/backpressure even when runtime queue health reported no available worker slots.

The continuation patch keeps the runtime policy strict:

- protected roots are evaluated before creating previews, approvals or TaskRuns;
- `forbidden_root` returns `blocked` and no ApprovalRequest is created;
- runtime queue saturation returns a visible `degraded` assistant response with `active_run_limit_reached`;
- legacy tests that expected execution/approval without an executable plan were aligned to the current governance contract.

Additional files changed:

- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
- `src/aipinho/api/routers/governance_lifecycle_router.py`
- `tests/contract/test_task_runtime_contracts.py`
- `tests/e2e/test_draft_preview_approval_lifecycle.py`
- `tests/integration/test_chat_runtime_parity_api.py`

Additional tests passed:

- `python -m pytest tests\integration\test_chat_runtime_parity_api.py::test_persistent_chat_forbidden_root_blocks_write tests\integration\test_chat_runtime_parity_api.py::test_active_run_limit_saturation_returns_visible_status -q`
  - 2 passed
- `python -m pytest tests\contract\test_task_runtime_contracts.py tests\contract\test_artifact_contracts.py tests\e2e\test_readonly_task_runtime_supervised_loop.py tests\e2e\test_draft_preview_approval_lifecycle.py tests\integration\test_chat_runtime_parity_api.py -q`
  - 15 passed
- `python -m pytest tests\unit\test_runtime_consistency_bindings.py tests\governance\test_runtime_vertical_slice.py tests\unit\test_workspace_runtime_context.py tests\unit\test_workflow_truth_runtime.py tests\unit\test_universal_task_session_service.py tests\governance\test_lifecycle_core.py -q`
  - 50 passed
- `python -m pytest tests\unit\test_artifact_runtime_service.py tests\unit\test_runtime_timeline_service.py tests\unit\test_task_runtime_service.py tests\unit\test_task_status_consistency_validator.py tests\unit\test_task_speaker_update_service.py tests\integration\test_task_runtime_api.py tests\integration\test_universal_artifact_registry_api.py -q`
  - 40 passed
- `python -m pytest tests\unit\test_runtime_consistency_bindings.py tests\governance\test_runtime_vertical_slice.py tests\e2e\test_readonly_task_runtime_supervised_loop.py -q`
  - 11 passed
- `python -m py_compile src\aipinho\services\governance\lifecycle\canonical_public_chat_service.py src\aipinho\api\routers\governance_lifecycle_router.py`
  - passed

Continuation verdict:

- `PUBLIC_ROUTE_PROTECTED_ROOT_GATE_READY`
- `CHAT_DISPATCH_BACKPRESSURE_VISIBLE_READY`
