# RD2 Regression Matrix

Status: RD2_REGRESSION_MATRIX_READY

Implemented domains:

- Intent
- Workspace
- Lifecycle
- Artifacts
- Approval
- Validation
- Completion
- SpeakerTruth
- Dispatcher
- Timeline
- ExecutionPlan
- Contracts
- RoleSelection
- Executor
- Models
- Tools
- Skills

Each matrix row reports:

- PASS
- WARN
- FAIL
- NOT_APPLICABLE

Each finding reports:

- regression id;
- category;
- description;
- expected contract;
- observed contract;
- severity;
- evidence;
- suspected modules.

Outputs:

- `regression_matrix.json` through the API payload
- `regression_matrix.csv` through `RuntimeDoctorReport.csv`
- `regression_summary.md` through `RuntimeDoctorReport.markdown`

Verification:

- `tests\unit\test_runtime_operator_ro.py` validates PASS/FAIL matrix behavior and the RD domains.
- SR/GR/RO/RD regression slice -> 50 passed
- runtime doctor legacy/consistency/timeline slice -> 18 passed
