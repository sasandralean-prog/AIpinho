# CONTROL B0.4.1 Public Runtime API Lazy Construction

## Verdict

CONTROL_B0_4_1_PUBLIC_RUNTIME_API_READINESS_LATENCY_CLOSED_READY_FOR_REVIEW

Updated B0.4 lifecycle verdict:

CONTROL_B0_4_GOVERNED_RUNTIME_LIFECYCLE_READY_FOR_REVIEW

## D1 Result

D1 confirmed the causal model. PublicRuntimeAPI construction was expensive per instance, not only on the first construction.

Key measurements:

- Full PublicRuntimeAPI(): average 3930.637 ms
- PublicRuntimeAPI with stub execution_bridge: average 0.055 ms
- Full PublicRuntimeExecutionBridge(): average 3965.615 ms
- Bridge with stub ReadonlyAnalysisArtifactRuntimeService and real TaskRuntimeService: average 1579.534 ms
- Bridge with real ReadonlyAnalysisArtifactRuntimeService and stub TaskRuntimeService: average 2326.265 ms
- Bridge with both stubbed: average 0.002 ms

The trivial readiness GET methods do not require PublicRuntimeExecutionBridge:

- version(): ApiVersionManager only
- contracts_view(): PublicContractRegistryService only
- modules(): ModuleLoader only
- runtime(): RuntimeKernel only
- handle(): uses the execution bridge and telemetry path

## C1 Corrective

Branch:

agent/codex/b0-4-1-public-runtime-api-lazy-construction

Preserved baseline:

8f04a24f465a44e0789243c38ce11631025c1d29

Final corrective commit:

reported_after_commit

PublicRuntimeAPI now keeps constructor-injected dependencies as optional per-instance cached fields. Each dependency is constructed only when the corresponding property is first used.

No router global singleton was introduced. Explicit dependency injection remains authoritative.

Post-patch PublicRuntimeAPI constructor average: 0.0007 ms.

## Live Validation

Governed Control Plane restart:

- operation_id: op_b041_restart_after_lazy_patch
- old PID: 29420
- new PID: 13228
- restart status: completed
- final lifecycle state: RUNNING_HEALTHY
- endpoint_health_ok: true
- readiness timeout changed: false

Sequential endpoint timing after patch:

- /docs: 200, first byte 16.849 ms, total 16.997 ms
- /openapi.json: 200, first byte 735.708 ms, total 753.856 ms
- /api/v1/version: 200, first byte 24.032 ms, total 24.095 ms
- /api/v1/contracts: 200, first byte 2.460 ms, total 2.581 ms
- /api/v1/modules: 200, first byte 2.168 ms, total 2.297 ms
- /api/v1/runtime: 200, first byte 9.689 ms, total 9.805 ms

The abandoned-request amplification condition is no longer triggered under normal readiness because the canonical endpoints complete comfortably inside the unchanged 3 second per-endpoint probe timeout.

## Validation

- python -m compileall -q src tests: PASS
- python -m pytest tests/unit/test_public_runtime_api_lazy_construction.py -q: PASS, 5 passed
- python -m pytest tests/unit/test_public_runtime_api_ex3.py -q: PASS, 9 passed
- python -m pytest tests/unit/test_public_analyze_response_boundary.py tests/unit/test_public_runtime_chat_route_boundary.py -q: PASS, 5 passed
- git diff --check: PASS

## Confirmations

- No readiness timeout inflation used.
- Background queue was not disabled.
- FireTest was not run.
- Control Plane authority was not broadened.
- Public response schemas were not intentionally changed.
- Runtime was restarted through the existing governed B0.4 lifecycle capability.

## Remaining Limitations

- Runtime acceptance was performed before commit from a dirty worktree so the live process could load the corrective code.
- A historical long-running task remains a separate diagnostic concern.
- Active Uvicorn log files could not be hashed with Get-FileHash because the process held them open.
