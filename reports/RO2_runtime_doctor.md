# RO2 Runtime Doctor

Status: RO2_RUNTIME_DOCTOR_READY

Implemented:

- `RuntimeOperatorDoctorService`
- `RuntimeDoctorReport`
- `RegressionFinding`
- `RegressionMatrix`
- deterministic Markdown and CSV outputs

Regression categories:

- Intent
- Lifecycle
- Workspace
- Artifacts
- Approval
- Validation
- Completion
- SpeakerTruth
- Dispatcher
- SemanticIR
- ExecutionPlan
- RoleSelection

Endpoint:

- `POST /api/v1/runtime/doctor/analyze`

The service is deterministic and read-only.

Verification:

- `tests\unit\test_runtime_operator_ro.py` covers deterministic regression matrix creation, PASS/FAIL/NOT_APPLICABLE rows, Markdown output, CSV output, and read-only/no-side-effect guarantees.
- Regression slice: 48 passed.
- Runtime consistency slice: 18 passed.
