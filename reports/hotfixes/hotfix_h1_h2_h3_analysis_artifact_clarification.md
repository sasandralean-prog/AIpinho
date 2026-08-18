# Hotfix H1-H3 - Analysis Contract, Artifact Separation and Clarification Bootstrap

- Date: 2026-07-08
- Verdicts:
  - `ANALYSIS_CONTRACT_READY`
  - `ARTIFACT_RUNTIME_SEPARATED`
  - `CLARIFICATION_GATE_BOOTSTRAP_READY`

## Objective

Prevent governed read-only analysis with artifact output from being promoted to `filesystem_write`, keep artifact generation separate from workspace mutation, and ensure a complete read-only analysis prompt can bootstrap a TaskRun without an invalid `needs_clarification` stop.

## Root Cause

The runtime had a safe vertical slice for read-only analysis artifacts, but the contract vocabulary did not expose a formal `analysis_readonly` contract. The existing `readonly_analysis` profile could execute safely, but prompts that mentioned reports/artifacts could still be interpreted by surrounding layers as file writing unless the path was routed through the dedicated vertical slice.

There was also a context issue discovered during validation: when a requested workspace lived under a registered workspace root, `WorkspaceContextService` replaced the requested target with the registry root. That could make analysis run against `C:\Dev\AIpinho` instead of the specific requested project folder.

## Changes

- Added `analysis_readonly` to runtime allowed contract types.
- Mapped `analysis_readonly` to the existing safe `readonly_analysis` runtime profile.
- Expanded `readonly_analysis.yaml` operation aliases to include `analysis_readonly`, `workspace_analysis_readonly`, and `readonly_analysis_with_artifact_output`.
- Updated canonical lifecycle defaults so workspace analysis read-only uses `contract_type=analysis_readonly` and `runtime_profile=readonly_analysis`.
- Updated canonical runtime expected outputs for read-only analysis artifacts.
- Updated `ReadonlyAnalysisArtifactRuntimeService` to create TaskRuns with `contract_type=analysis_readonly`.
- Fixed `WorkspaceContextService` so it preserves the requested workspace/project path while using the registered root only as an allowed boundary.

## Files Changed

- `C:\Dev\AIpinho\config\runtime\task_runtime_policy.yaml`
- `C:\Dev\AIpinho\config\runtime\profiles\readonly_analysis.yaml`
- `C:\Dev\AIpinho\src\aipinho\services\runtime\runtime_profile_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\runtime\task_runtime_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\runtime\workspace_context_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\governance\lifecycle\governance_lifecycle_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\governance\runtime\canonical_runtime_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\governance\runtime\readonly_analysis_artifact_runtime_service.py`
- `C:\Dev\AIpinho\tests\governance\test_runtime_vertical_slice.py`

## Tests

Passed:

- `python -m pytest tests\governance\test_runtime_vertical_slice.py -q`
  - `6 passed`
- `python -m pytest tests\unit\test_workspace_runtime_context.py tests\unit\test_workflow_truth_runtime.py -q`
  - `13 passed`
- `python -m pytest tests\governance\test_lifecycle_core.py tests\governance\test_g21_readonly_analysis_intent.py tests\unit\test_chat_operation_router_service.py -q`
  - `94 passed`
- `python -m py_compile ...`
  - passed

Legacy divergence:

- `python -m pytest tests\contract\test_task_runtime_contracts.py tests\contract\test_policy_kernel_contracts.py tests\unit\test_task_run_planner.py tests\unit\test_task_runtime_service.py -q`
  - `28 passed`, `1 failed`
  - Failing test: `test_runtime_accepts_write_profile_for_governed_file_write`
  - Cause: the test expects a `write_files` TaskRun without approval to remain `created`; current guard blocks it with `permission_requires_approval:write_files`.
  - Action: not relaxed in this hotfix because relaxing write without approval would conflict with current governed execution safety.

## Evidence

- Read-only artifact analysis now creates `TaskRun` with:
  - `contract_type=analysis_readonly`
  - `runtime_profile=readonly_analysis`
  - `requested_actions=["read_files"]`
  - `approval_required_for=[]`
  - `workspace_mutation=False`
  - `artifact_generation=True`
- Generated artifacts have real:
  - `artifact_id`
  - `storage_ref`
  - storage outside the analyzed workspace
- The analyzed workspace hash remains unchanged in the vertical slice test.
- Complete phase-1 read-only artifact prompts now create a TaskRun without `needs_clarification`.

## Success Contracts

`ANALYSIS_CONTRACT_READY`

Read-only analysis with artifact output no longer needs `filesystem_write` or `write_file`.

`ARTIFACT_RUNTIME_SEPARATED`

Artifacts are generated in the governed artifact store and are not workspace mutation.

`CLARIFICATION_GATE_BOOTSTRAP_READY`

Complete read-only analysis prompts bootstrap TaskRun and runtime state instead of stopping at invalid clarification.

