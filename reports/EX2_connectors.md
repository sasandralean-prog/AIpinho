# EX2 External Connector Framework

Status: EX2_READY.

## Scope

Implemented a standardized connector framework for external clients.

## Files

- `src/aipinho/schemas/external_connector.py`
- `src/aipinho/services/external_connector_service.py`
- `src/aipinho/api/routers/external_gateway_router.py`
- `tests/unit/test_external_connector_ex2.py`
- `docs/external/connector_framework.md`
- `reports/connector_registry.json`

## Invariants

- Connectors do not execute Runtime.
- Connectors do not modify contracts.
- Connectors communicate through the Gateway.
- Official connectors share one contract format.

## Verification

- `python -m pytest tests\unit\test_external_connector_ex2.py -q`
  - Result: 6 passed.
- `python -m compileall src\aipinho\schemas\external_connector.py src\aipinho\services\external_connector_service.py src\aipinho\api\routers\external_gateway_router.py`
  - Result: passed.
- `python -m pytest tests\unit\test_external_gateway_ex1.py tests\unit\test_external_connector_ex2.py tests\unit\test_runtime_kernel_kr.py tests\unit\test_runtime_telemetry_ob1.py tests\unit\test_runtime_metrics_ob2.py tests\unit\test_runtime_dashboard_ob3.py tests\unit\test_cognitive_policy_engine_cg1.py tests\unit\test_cognitive_router_cg2.py tests\unit\test_cognitive_escalation_cg3.py tests\unit\test_cognitive_governance_controller_cg4.py -q`
  - Result: 57 passed.
- Router registration check:
  - Router count: 139.
  - `/api/v1/external` registered: true.

## Verdict

EX2_READY
