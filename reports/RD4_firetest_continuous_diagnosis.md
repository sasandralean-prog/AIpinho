# RD4 Fire Test Continuous Diagnosis

Status: RD4_FIRETEST_CONTINUOUS_DIAGNOSIS_READY

Implemented:

- `FireTestDoctorService`
- `FireTestDoctorAnalyzeRequest`
- `FireTestDoctorResult`

Endpoint:

- `POST /api/v1/runtime/firetest/analyze`

Pipeline:

```text
FireTest RAW
-> RuntimeSnapshot
-> RuntimeDoctorReport
-> RegressionMatrix
-> RuntimePatchPlan
```

Inputs supported:

- raw runtime data;
- Universal Task Session fragments;
- expected contract;
- source hints.

Outputs:

- Doctor Report;
- Regression Matrix;
- Patch Plan.

Safety:

- read-only;
- no runtime mutation;
- no patch application;
- no approval changes.

Verification:

- `tests\unit\test_runtime_operator_ro.py` validates the full FireTest Doctor pipeline.
- SR/GR/RO/RD regression slice -> 50 passed
- runtime doctor legacy/consistency/timeline slice -> 18 passed
