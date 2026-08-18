# RD3 Runtime Patch Planner

Status: RD3_RUNTIME_PATCH_PLANNER_READY

Implemented:

- `RuntimePatchPlannerService`
- `RuntimePatchPlan`
- `PatchPlanItem`

Endpoint:

- `POST /api/v1/runtime/doctor/patch-plan`

PatchPlan contains:

- module;
- files/modules affected;
- impact through reason/risk;
- rollback;
- tests needed;
- confidence;
- priority through risk.

Safety:

- never emits `apply_patch`;
- never writes files;
- never runs git;
- never executes shell;
- `applies_patch` is always false.

Verification:

- `tests\unit\test_runtime_operator_ro.py` verifies advisory-only patch planning.
- SR/GR/RO/RD regression slice -> 50 passed
- runtime doctor legacy/consistency/timeline slice -> 18 passed
