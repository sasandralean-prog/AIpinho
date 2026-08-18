# Runtime Operator RO1-RO4

## Scope

The Runtime Operator is a read-only introspection layer for the governed runtime.
It does not execute tools, create tasks, approve requests, write files, apply patches, or run shell commands.

## RO1 Runtime Operator

`RuntimeOperatorService` creates a `RuntimeSnapshot` with:

- current intent;
- lifecycle;
- contracts;
- roles;
- workspace;
- validation;
- completion;
- speaker truth;
- artifacts;
- semantic IR;
- execution plan;
- approval;
- dispatcher;
- timeline.

Endpoint:

- `GET /api/v1/runtime/operator/snapshot`
- `POST /api/v1/runtime/operator/snapshot`

## RO2 Runtime Doctor

`RuntimeOperatorDoctorService` compares a `RuntimeSnapshot` against an `ExpectedRuntimeContract`.
It emits:

- `RuntimeDoctorReport`;
- `RegressionMatrix`;
- `RegressionFinding`;
- Markdown summary;
- CSV matrix.

Endpoint:

- `POST /api/v1/runtime/doctor/analyze`

The Doctor is deterministic and does not use LLMs.

## RO3 Runtime Explainer

`RuntimeExplainerService` converts a Doctor report into an operator-facing explanation.
It is advisory only.

Endpoint:

- `POST /api/v1/runtime/doctor/explain`

It cannot decide execution, approve, patch, or alter runtime state.

## RO4 Runtime Patch Planner

`RuntimePatchPlannerService` creates a patch plan from Doctor findings.
It never applies the patch.

Endpoint:

- `POST /api/v1/runtime/doctor/patch-plan`

The output includes suspected modules, reasons, risks, rollback notes, and tests.

## RD1-RD4 Runtime Doctor

The Runtime Doctor extends the operator pipeline into a continuous diagnosis path:

```text
RuntimeSnapshot
-> RuntimeDoctorReport
-> RegressionMatrix
-> RuntimePatchPlan
```

`FireTestDoctorService` wraps the complete path for fire-test payloads:

```text
FireTest RAW
-> RuntimeSnapshot
-> RuntimeDoctorReport
-> RegressionMatrix
-> RuntimePatchPlan
```

Endpoints:

- `GET /api/v1/runtime/doctor`
- `POST /api/v1/runtime/doctor/analyze`
- `POST /api/v1/runtime/doctor/patch-plan`
- `POST /api/v1/runtime/firetest/analyze`

The Doctor measures, diagnoses, and proves contract regressions. It does not correct, patch, approve, execute, or mutate state.
