# Model-Assisted Patch Planning Integration

Generated: 2026-06-21T23:45:20-03:00

## Objective

Connect the configured `patch_planner` role/model to the canonical `PatchPlanningService` without granting the model filesystem write, patch apply, shell, network, or approval authority.

## Root Cause

`GovernedTaskStepRunner.execute_patch_pipeline` previously attempted only narrow local file actions. When neither explicit filename parsing nor the UI-text fallback identified a target, the runtime ended in `patch_plan_missing`. The canonical patch planner could build a validated preview, but no model-assisted adapter supplied it with a bounded file context and an explicit replacement.

## Implementation

- Added `config/patching/model_patch_planner_policy.yaml`.
- Added `schemas/patching/model_patch_proposal.py`.
- Added `services/patching/model_assisted_patch_planner_service.py`.
- Added `POST /api/v1/patch-plans/model-assisted`.
- Integrated the service as the fallback path after existing deterministic local action planning in `GovernedTaskStepRunner`.

The adapter reads only an already supplied or policy-bounded `FileContextBundle`, asks role `patch_planner` for a single JSON proposal, validates that the proposed file was in the supplied context and that its replacement differs from the current content, then delegates diff construction, target guarding, evidence normalization, risk assessment, and validation to `PatchPlanningService`.

## Safety Contract

- The model receives a read-only context only.
- The model cannot execute tools, write files, apply a patch, use shell, access network, or grant approval.
- Invalid, empty, unchanged, out-of-context, fallback, or non-completed model proposals are blocked with structured reasons.
- The resulting plan remains preview-only: `apply_enabled=false`, `write_enabled=false`.
- Patch apply remains owned by the existing quality-gate and approval bridge.

## Validation

Executed:

```text
python -m py_compile src\\aipinho\\schemas\\patching\\model_patch_proposal.py src\\aipinho\\services\\patching\\model_assisted_patch_planner_service.py src\\aipinho\\services\\runtime\\governed_task_step_runner.py src\\aipinho\\api\\routers\\patch_planning_router.py
python -m pytest tests\\unit\\test_model_assisted_patch_planner_service.py tests\\unit\\test_task_run_executor.py -q
```

Result: `7 passed`.

## Remaining Boundary

This integration creates a governed patch preview. A request to apply that preview must still traverse the existing patch quality gate and approval bridge; it is intentionally not auto-applied by the task step.
