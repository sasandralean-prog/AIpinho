# EX1 External Gateway

Status: EX1_READY.

## Scope

Implemented the canonical External Gateway for external clients.

## Files

- `src/aipinho/schemas/external_gateway.py`
- `src/aipinho/services/external_gateway_service.py`
- `src/aipinho/api/routers/external_gateway_router.py`
- `src/aipinho/api/routers/__init__.py`
- `tests/unit/test_external_gateway_ex1.py`
- `docs/external/external_gateway.md`
- `reports/gateway_contract.json`

## Invariants

- External clients cannot access internal modules directly.
- Gateway validates client type, version, contract keys, and target module.
- Gateway dispatches only to Kernel Runtime.
- No Runtime mutation from the Gateway layer.

## Verification

- `python -m pytest tests\unit\test_external_gateway_ex1.py -q`
  - Result: 6 passed.
- `python -m compileall src\aipinho\schemas\external_gateway.py src\aipinho\services\external_gateway_service.py src\aipinho\api\routers\external_gateway_router.py src\aipinho\api\routers\__init__.py`
  - Result: passed.
- `python -m pytest tests\unit\test_external_gateway_ex1.py tests\unit\test_runtime_kernel_kr.py tests\unit\test_runtime_telemetry_ob1.py tests\unit\test_runtime_metrics_ob2.py tests\unit\test_runtime_dashboard_ob3.py tests\unit\test_cognitive_policy_engine_cg1.py tests\unit\test_cognitive_router_cg2.py tests\unit\test_cognitive_escalation_cg3.py tests\unit\test_cognitive_governance_controller_cg4.py -q`
  - Result: 51 passed.
- Router registration check:
  - Router count: 139.
  - `/api/v1/external` registered: true.

## Verdict

EX1_READY
