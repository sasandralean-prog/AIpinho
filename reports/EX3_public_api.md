# EX3 Public Runtime API

Status: EX3_READY.

## Scope

Implemented the official public Runtime API surface.

## Files

- `src/aipinho/schemas/public_runtime_api.py`
- `src/aipinho/services/public_runtime_api_service.py`
- `src/aipinho/api/routers/public_runtime_api_router.py`
- `src/aipinho/api/routers/__init__.py`
- `tests/unit/test_public_runtime_api_ex3.py`
- `docs/external/public_runtime_api.md`
- `reports/openapi.yaml`
- `reports/public_contracts.json`

## Invariants

- All operational requests pass through Gateway.
- Gateway dispatches to Runtime Kernel.
- Public contracts are versioned.
- API audit and telemetry are recorded.

## Verification

- `python -m pytest tests\unit\test_public_runtime_api_ex3.py -q`
  - Result: 6 passed.
- `python -m compileall src\aipinho\schemas\public_runtime_api.py src\aipinho\services\public_runtime_api_service.py src\aipinho\api\routers\public_runtime_api_router.py src\aipinho\api\routers\__init__.py`
  - Result: passed.
- `python -m pytest tests\unit\test_external_gateway_ex1.py tests\unit\test_external_connector_ex2.py tests\unit\test_public_runtime_api_ex3.py tests\unit\test_runtime_kernel_kr.py tests\unit\test_runtime_telemetry_ob1.py tests\unit\test_runtime_metrics_ob2.py tests\unit\test_runtime_dashboard_ob3.py tests\unit\test_cognitive_policy_engine_cg1.py tests\unit\test_cognitive_router_cg2.py tests\unit\test_cognitive_escalation_cg3.py tests\unit\test_cognitive_governance_controller_cg4.py -q`
  - Result: 63 passed.
- Router registration check:
  - Router count: 140.
  - `/api/v1` public API router registered: true.
  - `/api/v1/external` gateway router registered: true.

## Verdict

EX3_READY
