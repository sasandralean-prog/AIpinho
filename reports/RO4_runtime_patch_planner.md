# RO4 Runtime Patch Planner

Status: RO4_RUNTIME_PATCH_PLANNER_READY

Implemented:

- `RuntimePatchPlannerService`
- `RuntimePatchPlan`
- `PatchPlanItem`

Endpoint:

- `POST /api/v1/runtime/doctor/patch-plan`

Patch Planner output includes:

- suspected files/modules;
- reason;
- risk;
- rollback;
- tests;
- confidence.

The planner never applies patches. Codex or another governed executor must apply any future patch through the normal approval/runtime path.

Verification:

- `tests\unit\test_runtime_operator_ro.py` verifies patch plans are advisory, include suspected modules/tests/rollback, and `applies_patch` remains false.
- Regression slice: 48 passed.
